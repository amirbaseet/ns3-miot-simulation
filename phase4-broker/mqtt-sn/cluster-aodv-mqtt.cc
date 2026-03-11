/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Priority-Aware MQTT-SN for MIoT (with Broker/Sink)
 * =====================================================
 * 201 Nodes | 180 Sensors | 20 CH/Gateway | 1 Broker/Sink
 * AODV | MQTT-SN | Priority Queue | Emergency Detection
 *
 * Data Flow:
 *   [180 Sensors] --MQTT-SN--> [20 Gateways] --Forward--> [1 Broker/Sink]
 *
 * Build:
 *   cp *.h *.cc ~/ns-3-dev/scratch/cluster-aodv-mqtt/
 *   cd ~/ns-3-dev && ./ns3 build
 *   ./ns3 run cluster-aodv-mqtt
 */

#include "mqtt-sn-header.h"
#include "mqtt-sn-publisher.h"
#include "mqtt-sn-gateway.h"
#include "mqtt-sn-broker.h"

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/aodv-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"

#include <cmath>
#include <vector>
#include <fstream>
#include <iomanip>
#include <algorithm>
#include <limits>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("ClusterAodvMqtt");

static const uint32_t N_ECG  = 60, N_HR = 60, N_TEMP = 60;
static const uint32_t N_REG  = N_ECG + N_HR + N_TEMP;  // 180
static const uint32_t N_CH   = 20;
static const uint32_t N_SINK = 1;
static const uint32_t N_TOT  = N_REG + N_CH + N_SINK;  // 201
static const double   AREA   = 1000.0;
static const uint32_t COLS   = 5, ROWS = 4;
static const double   SIM_T  = 100.0;
static const uint16_t MQTT_PORT   = 1883;  // Sensor -> Gateway
static const uint16_t BROKER_PORT = 1884;  // Gateway -> Broker
static const double   EMERGENCY_PROB = 0.005;

std::vector<uint32_t> cAssign (N_REG, 0);
std::vector<uint32_t> cSizes (N_CH, 0);

static double CalcDist (const Vector &a, const Vector &b)
{ return std::sqrt ((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y)); }

// ============================================================
//  STEP 1: Create 201 Nodes
// ============================================================
void CreateNodes (NodeContainer &sens, NodeContainer &chs,
                  NodeContainer &sink, NodeContainer &all)
{
  sens.Create (N_REG);
  chs.Create (N_CH);
  sink.Create (N_SINK);
  // Order: sensors(0-179), CHs(180-199), sink(200)
  all.Add (sens);
  all.Add (chs);
  all.Add (sink);
}

// ============================================================
//  STEP 2: WiFi
// ============================================================
NetDeviceContainer ConfigWifi (NodeContainer &all, YansWifiPhyHelper &phy)
{
  WifiHelper w; w.SetStandard (WIFI_STANDARD_80211b);
  w.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
    "DataMode", StringValue ("DsssRate11Mbps"),
    "ControlMode", StringValue ("DsssRate1Mbps"));
  YansWifiChannelHelper ch;
  ch.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  ch.AddPropagationLoss ("ns3::LogDistancePropagationLossModel",
    "Exponent", DoubleValue (2.5), "ReferenceDistance", DoubleValue (1.0),
    "ReferenceLoss", DoubleValue (46.6777));
  phy.SetChannel (ch.Create ());
  phy.Set ("TxPowerStart", DoubleValue (20.0));
  phy.Set ("TxPowerEnd", DoubleValue (20.0));
  WifiMacHelper mac; mac.SetType ("ns3::AdhocWifiMac");
  return w.Install (phy, mac, all);
}

// ============================================================
//  STEP 3: AODV + IP
// ============================================================
Ipv4InterfaceContainer InstallStack (NodeContainer &all, NetDeviceContainer &dev)
{
  AodvHelper aodv;
  aodv.Set ("HelloInterval", TimeValue (Seconds (2)));
  aodv.Set ("AllowedHelloLoss", UintegerValue (3));
  aodv.Set ("ActiveRouteTimeout", TimeValue (Seconds (15)));
  aodv.Set ("RreqRetries", UintegerValue (5));
  aodv.Set ("NetDiameter", UintegerValue (20));
  aodv.Set ("NodeTraversalTime", TimeValue (MilliSeconds (100)));
  InternetStackHelper inet; inet.SetRoutingHelper (aodv); inet.Install (all);
  Ipv4AddressHelper addr; addr.SetBase ("10.1.0.0", "255.255.0.0");
  return addr.Assign (dev);
}

// ============================================================
//  STEP 4: Position Nodes
// ============================================================
void PositionNodes (NodeContainer &sens, NodeContainer &chs, NodeContainer &sink)
{
  MobilityHelper m; m.SetMobilityModel ("ns3::ConstantPositionMobilityModel");

  // CHs: 4x5 grid
  Ptr<ListPositionAllocator> cp = CreateObject<ListPositionAllocator> ();
  double cW = AREA/COLS, cH = AREA/ROWS;
  for (uint32_t i = 0; i < N_CH; i++)
    cp->Add (Vector ((i%COLS+0.5)*cW, (i/COLS+0.5)*cH, 0));
  m.SetPositionAllocator (cp); m.Install (chs);

  // Sensors: random
  Ptr<ListPositionAllocator> sp = CreateObject<ListPositionAllocator> ();
  Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable> ();
  rx->SetAttribute ("Min", DoubleValue (0)); rx->SetAttribute ("Max", DoubleValue (AREA));
  Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable> ();
  ry->SetAttribute ("Min", DoubleValue (0)); ry->SetAttribute ("Max", DoubleValue (AREA));
  for (uint32_t i = 0; i < N_REG; i++)
    sp->Add (Vector (rx->GetValue (), ry->GetValue (), 0));
  m.SetPositionAllocator (sp); m.Install (sens);

  // Sink/Broker: center
  Ptr<ListPositionAllocator> skp = CreateObject<ListPositionAllocator> ();
  skp->Add (Vector (AREA/2.0, AREA/2.0, 0));
  m.SetPositionAllocator (skp); m.Install (sink);
}

// ============================================================
//  STEP 5: Cluster Assignment
// ============================================================
void AssignClusters (NodeContainer &sens, NodeContainer &chs)
{
  std::vector<Vector> chP (N_CH);
  for (uint32_t i = 0; i < N_CH; i++)
    chP[i] = chs.Get (i)->GetObject<MobilityModel> ()->GetPosition ();
  std::fill (cSizes.begin (), cSizes.end (), 0);
  for (uint32_t n = 0; n < N_REG; n++)
    {
      Vector np = sens.Get (n)->GetObject<MobilityModel> ()->GetPosition ();
      double md = 1e9; uint32_t ne = 0;
      for (uint32_t c = 0; c < N_CH; c++)
        { double d = CalcDist (np, chP[c]); if (d < md) { md = d; ne = c; } }
      cAssign[n] = ne; cSizes[ne]++;
    }
  std::cout << "  Clusters: min=" << *std::min_element (cSizes.begin (), cSizes.end ())
            << " max=" << *std::max_element (cSizes.begin (), cSizes.end ())
            << " avg=" << std::fixed << std::setprecision (1)
            << (double)N_REG/N_CH << "\n";
}

// ============================================================
//  STEP 6: Install MQTT-SN (Publisher + Gateway + Broker)
// ============================================================
void InstallMqtt (NodeContainer &sens, NodeContainer &chs,
                  NodeContainer &sink, Ipv4InterfaceContainer &ifaces)
{
  // Broker/Sink IP (index = N_REG + N_CH = 200)
  uint32_t sinkIfIdx = N_REG + N_CH;
  Ipv4Address brokerAddr = ifaces.GetAddress (sinkIfIdx);

  // ---- Install Broker on Sink ----
  Ptr<MqttSnBroker> broker = CreateObject<MqttSnBroker> ();
  broker->Setup (BROKER_PORT);
  sink.Get (0)->AddApplication (broker);
  broker->SetStartTime (Seconds (0));
  broker->SetStopTime (Seconds (SIM_T));

  // ---- Install Gateways on CHs (with broker forwarding) ----
  for (uint32_t c = 0; c < N_CH; c++)
    {
      Ptr<MqttSnGateway> gw = CreateObject<MqttSnGateway> ();
      gw->Setup (MQTT_PORT);
      gw->SetBroker (brokerAddr, BROKER_PORT);  // Enable forwarding to broker
      chs.Get (c)->AddApplication (gw);
      gw->SetStartTime (Seconds (0));
      gw->SetStopTime (Seconds (SIM_T));
    }

  // ---- Install Publishers on Sensors ----
  Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable> ();
  rng->SetAttribute ("Min", DoubleValue (5.0));
  rng->SetAttribute ("Max", DoubleValue (20.0));

  uint32_t ecg = 0, hr = 0, tmp = 0;
  for (uint32_t n = 0; n < N_REG; n++)
    {
      uint32_t chIf = N_REG + cAssign[n];
      Ipv4Address gwAddr = ifaces.GetAddress (chIf);

      uint16_t topic; Time interval; uint32_t payload; uint8_t qos;
      if (n < N_ECG) {
        topic = TOPIC_ECG; interval = MilliSeconds (250);
        payload = 128; qos = PRIORITY_HIGH; ecg++;
      } else if (n < N_ECG + N_HR) {
        topic = TOPIC_HEART_RATE; interval = Seconds (1.0);
        payload = 64; qos = PRIORITY_MEDIUM; hr++;
      } else {
        topic = TOPIC_TEMPERATURE; interval = Seconds (5.0);
        payload = 32; qos = PRIORITY_LOW; tmp++;
      }

      Ptr<MqttSnPublisher> pub = CreateObject<MqttSnPublisher> ();
      pub->Setup (gwAddr, MQTT_PORT, topic, interval, payload, qos);
      pub->EnableEmergencyDetection (EMERGENCY_PROB);
      sens.Get (n)->AddApplication (pub);
      pub->SetStartTime (Seconds (rng->GetValue ()));
      pub->SetStopTime (Seconds (SIM_T - 2.0));
    }

  std::cout << "\n  MQTT-SN Configuration:\n"
            << "    ECG:         " << ecg << " nodes | QoS=2 HIGH     | 250ms | 128B\n"
            << "    Heart Rate:  " << hr  << " nodes | QoS=1 MEDIUM   | 1s    | 64B\n"
            << "    Temperature: " << tmp << " nodes | QoS=0 LOW      | 5s    | 32B\n"
            << "    Gateways:    " << N_CH << " CHs (port " << MQTT_PORT << ")\n"
            << "    Broker:      1 sink (port " << BROKER_PORT << ") at center\n"
            << "    Emergency:   " << (EMERGENCY_PROB*100) << "% per publish\n"
            << "    Data Flow:   Sensor -> Gateway -> Broker\n\n";
}

// ============================================================
//  STEP 7: Results
// ============================================================
void PrintResults (Ptr<FlowMonitor> fm, FlowMonitorHelper &fh,
                   NodeContainer &chs, NodeContainer &sink)
{
  fm->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> cls = DynamicCast<Ipv4FlowClassifier> (fh.GetClassifier ());
  auto stats = fm->GetFlowStats ();

  uint64_t tTx = 0, tRx = 0, tRxB = 0;
  double tDel = 0; uint32_t fl = 0, dead = 0;

  std::ofstream csv ("mqtt-sn-broker-results.csv");
  csv << "FlowID,SrcAddr,DstAddr,TxPackets,RxPackets,LostPackets,"
      << "PDR_pct,Throughput_kbps,AvgDelay_ms,AvgJitter_ms\n";

  for (auto &kv : stats)
    {
      auto ft = cls->FindFlow (kv.first); auto &s = kv.second;
      double pdr = s.txPackets > 0 ? (double)s.rxPackets/s.txPackets*100 : 0;
      double dur = s.rxPackets > 0 ? (s.timeLastRxPacket-s.timeFirstTxPacket).GetSeconds () : 0;
      double tp = dur > 0 ? s.rxBytes*8.0/dur/1000 : 0;
      double dl = s.rxPackets > 0 ? s.delaySum.GetMilliSeconds ()/(double)s.rxPackets : 0;
      double jt = s.rxPackets > 1 ? s.jitterSum.GetMilliSeconds ()/(double)(s.rxPackets-1) : 0;
      tTx += s.txPackets; tRx += s.rxPackets; tRxB += s.rxBytes;
      tDel += s.rxPackets > 0 ? s.delaySum.GetMilliSeconds () : 0;
      fl++; if (s.rxPackets == 0) dead++;
      csv << kv.first << "," << ft.sourceAddress << "," << ft.destinationAddress
          << "," << s.txPackets << "," << s.rxPackets << "," << s.lostPackets
          << "," << std::fixed << std::setprecision (2)
          << pdr << "," << tp << "," << dl << "," << jt << "\n";
    }
  csv.close ();

  double pdr = tTx > 0 ? (double)tRx/tTx*100 : 0;
  double avgD = tRx > 0 ? tDel/tRx : 0;

  std::cout << "============================================================\n"
    << "  MQTT-SN + BROKER SIMULATION RESULTS\n"
    << "============================================================\n"
    << "  Flows: " << fl << " (dead: " << dead << ")\n"
    << "  Tx: " << tTx << " | Rx: " << tRx << "\n"
    << "  PDR: " << std::fixed << std::setprecision (2) << pdr << "%\n"
    << "  Avg Delay: " << avgD << " ms\n"
    << "  Throughput: " << (tRxB*8.0/SIM_T/1000) << " kbps\n"
    << "============================================================\n\n";

  // Per-Gateway Stats
  std::cout << "  Per-Gateway Statistics:\n"
            << "  -----------------------\n";
  uint32_t totalEmerg = 0, totalFwd = 0;
  for (uint32_t c = 0; c < N_CH; c++)
    {
      Ptr<MqttSnGateway> gw = DynamicCast<MqttSnGateway> (chs.Get (c)->GetApplication (0));
      if (gw) {
        gw->PrintStats ();
        totalEmerg += gw->GetStats ().emergencies;
        totalFwd += gw->GetStats ().forwardedToBroker;
      }
    }

  // Broker Stats
  Ptr<MqttSnBroker> br = DynamicCast<MqttSnBroker> (sink.Get (0)->GetApplication (0));
  if (br) br->PrintStats ();

  std::cout << "  Total Emergencies: " << totalEmerg << "\n"
            << "  Total Forwarded to Broker: " << totalFwd << "\n"
            << "  Output: mqtt-sn-broker-results.csv\n"
            << "============================================================\n\n";

  fm->SerializeToXmlFile ("mqtt-sn-broker-flowmon.xml", true, true);
}

// ============================================================
//  MAIN
// ============================================================
int main (int argc, char *argv[])
{
  double simTime = SIM_T;
  bool enableAnim = true, verbose = false;

  CommandLine cmd (__FILE__);
  cmd.AddValue ("simTime", "Sim time", simTime);
  cmd.AddValue ("anim", "NetAnim", enableAnim);
  cmd.AddValue ("verbose", "Verbose", verbose);
  cmd.Parse (argc, argv);

  if (verbose) {
    LogComponentEnable ("ClusterAodvMqtt", LOG_LEVEL_INFO);
    LogComponentEnable ("MqttSnPublisher", LOG_LEVEL_INFO);
    LogComponentEnable ("MqttSnGateway", LOG_LEVEL_INFO);
    LogComponentEnable ("MqttSnBroker", LOG_LEVEL_INFO);
  }

  SeedManager::SetSeed (42); SeedManager::SetRun (1);

  std::cout << "\n============================================================\n"
    << "  MQTT-SN for MIoT (with Broker/Sink)\n"
    << "  Sensors: " << N_REG << " (" << N_ECG << " ECG + "
    << N_HR << " HR + " << N_TEMP << " Temp)\n"
    << "  Gateways: " << N_CH << " | Broker: " << N_SINK
    << " | Total: " << N_TOT << "\n"
    << "  Flow: Sensor -> Gateway -> Broker\n"
    << "  Area: " << AREA << "x" << AREA << "m | AODV | " << simTime << "s\n"
    << "============================================================\n\n";

  // Build
  NodeContainer sens, chs, sink, all;
  CreateNodes (sens, chs, sink, all);

  YansWifiPhyHelper phy;
  NetDeviceContainer dev = ConfigWifi (all, phy);
  Ipv4InterfaceContainer ifaces = InstallStack (all, dev);

  PositionNodes (sens, chs, sink);
  AssignClusters (sens, chs);
  InstallMqtt (sens, chs, sink, ifaces);

  FlowMonitorHelper fh;
  Ptr<FlowMonitor> fm = fh.InstallAll ();

  // NetAnim
  AnimationInterface *anim = nullptr;
  if (enableAnim)
    {
      anim = new AnimationInterface ("mqtt-sn-broker-animation.xml");
      anim->SetMaxPktsPerTraceFile (500000);
      // ECG = Red
      for (uint32_t i = 0; i < N_ECG; i++) {
        anim->UpdateNodeDescription (sens.Get (i), "ECG[H]");
        anim->UpdateNodeColor (sens.Get (i), 255, 59, 48);
        anim->UpdateNodeSize (sens.Get (i)->GetId (), 8, 8);
      }
      // HR = Blue
      for (uint32_t i = N_ECG; i < N_ECG+N_HR; i++) {
        anim->UpdateNodeDescription (sens.Get (i), "HR[M]");
        anim->UpdateNodeColor (sens.Get (i), 0, 122, 255);
        anim->UpdateNodeSize (sens.Get (i)->GetId (), 8, 8);
      }
      // Temp = Green
      for (uint32_t i = N_ECG+N_HR; i < N_REG; i++) {
        anim->UpdateNodeDescription (sens.Get (i), "Tmp[L]");
        anim->UpdateNodeColor (sens.Get (i), 52, 199, 89);
        anim->UpdateNodeSize (sens.Get (i)->GetId (), 8, 8);
      }
      // Gateways = Purple
      for (uint32_t i = 0; i < N_CH; i++) {
        anim->UpdateNodeDescription (chs.Get (i),
          "GW" + std::to_string (i) + "[" + std::to_string (cSizes[i]) + "]");
        anim->UpdateNodeColor (chs.Get (i), 175, 82, 222);
        anim->UpdateNodeSize (chs.Get (i)->GetId (), 25, 25);
      }
      // Broker/Sink = Gold
      anim->UpdateNodeDescription (sink.Get (0), "BROKER");
      anim->UpdateNodeColor (sink.Get (0), 255, 204, 0);
      anim->UpdateNodeSize (sink.Get (0)->GetId (), 40, 40);
    }

  std::cout << "[RUN] Simulating " << simTime << "s...\n";
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  PrintResults (fm, fh, chs, sink);

  Simulator::Destroy ();
  if (anim) delete anim;

  std::cout << "[DONE]\n\n";
  return 0;
}
