/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Priority-Aware MQTT-SN for MIoT (Scalability Version)
 * =======================================================
 * Supports command-line node count for experiments:
 *   ./ns3 run "cluster-aodv-mqtt --nSensors=50 --nCH=5"
 *   ./ns3 run "cluster-aodv-mqtt --nSensors=100 --nCH=10"
 *   ./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20"
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
#include <sstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("ClusterAodvMqtt");

static const double   AREA   = 1000.0;
static const double   SIM_T  = 100.0;
static const uint16_t MQTT_PORT   = 1883;
static const uint16_t BROKER_PORT = 1884;
static const double   EMERGENCY_PROB = 0.005;

// Dynamic vectors (sized at runtime)
std::vector<uint32_t> cAssign;
std::vector<uint32_t> cSizes;

static double CalcDist (const Vector &a, const Vector &b)
{ return std::sqrt ((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y)); }

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

void PositionNodes (NodeContainer &sens, NodeContainer &chs, NodeContainer &sink,
                    uint32_t nCH)
{
  MobilityHelper m; m.SetMobilityModel ("ns3::ConstantPositionMobilityModel");

  // CH grid: auto calculate rows/cols
  uint32_t cols = (uint32_t)std::ceil (std::sqrt ((double)nCH * AREA / AREA));
  if (cols < 1) cols = 1;
  uint32_t rows = (nCH + cols - 1) / cols;

  Ptr<ListPositionAllocator> cp = CreateObject<ListPositionAllocator> ();
  double cW = AREA / cols, cH = AREA / rows;
  for (uint32_t i = 0; i < nCH; i++)
    cp->Add (Vector ((i%cols+0.5)*cW, (i/cols+0.5)*cH, 0));
  m.SetPositionAllocator (cp); m.Install (chs);

  // Sensors: random
  uint32_t nSens = sens.GetN ();
  Ptr<ListPositionAllocator> sp = CreateObject<ListPositionAllocator> ();
  Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable> ();
  rx->SetAttribute ("Min", DoubleValue (0)); rx->SetAttribute ("Max", DoubleValue (AREA));
  Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable> ();
  ry->SetAttribute ("Min", DoubleValue (0)); ry->SetAttribute ("Max", DoubleValue (AREA));
  for (uint32_t i = 0; i < nSens; i++)
    sp->Add (Vector (rx->GetValue (), ry->GetValue (), 0));
  m.SetPositionAllocator (sp); m.Install (sens);

  // Sink: center
  Ptr<ListPositionAllocator> skp = CreateObject<ListPositionAllocator> ();
  skp->Add (Vector (AREA/2.0, AREA/2.0, 0));
  m.SetPositionAllocator (skp); m.Install (sink);
}

void AssignClusters (NodeContainer &sens, NodeContainer &chs, uint32_t nCH)
{
  uint32_t nSens = sens.GetN ();
  cAssign.resize (nSens, 0);
  cSizes.resize (nCH, 0);

  std::vector<Vector> chP (nCH);
  for (uint32_t i = 0; i < nCH; i++)
    chP[i] = chs.Get (i)->GetObject<MobilityModel> ()->GetPosition ();
  std::fill (cSizes.begin (), cSizes.end (), 0);

  for (uint32_t n = 0; n < nSens; n++)
    {
      Vector np = sens.Get (n)->GetObject<MobilityModel> ()->GetPosition ();
      double md = 1e9; uint32_t ne = 0;
      for (uint32_t c = 0; c < nCH; c++)
        { double d = CalcDist (np, chP[c]); if (d < md) { md = d; ne = c; } }
      cAssign[n] = ne; cSizes[ne]++;
    }
  std::cout << "  Clusters: min=" << *std::min_element (cSizes.begin (), cSizes.end ())
            << " max=" << *std::max_element (cSizes.begin (), cSizes.end ())
            << " avg=" << std::fixed << std::setprecision (1)
            << (double)nSens/nCH << "\n";
}

void InstallMqtt (NodeContainer &sens, NodeContainer &chs, NodeContainer &sink,
                  Ipv4InterfaceContainer &ifaces, uint32_t nSens, uint32_t nCH,
                  bool useBroker, uint32_t nECGin, uint32_t nHRin)
{
  uint32_t sinkIfIdx = nSens + nCH;
  Ipv4Address brokerAddr = ifaces.GetAddress (sinkIfIdx);

  // Broker on sink
  if (useBroker)
    {
      Ptr<MqttSnBroker> broker = CreateObject<MqttSnBroker> ();
      broker->Setup (BROKER_PORT);
      sink.Get (0)->AddApplication (broker);
      broker->SetStartTime (Seconds (0));
      broker->SetStopTime (Seconds (SIM_T));
    }

  // Gateways on CHs
  for (uint32_t c = 0; c < nCH; c++)
    {
      Ptr<MqttSnGateway> gw = CreateObject<MqttSnGateway> ();
      gw->Setup (MQTT_PORT);
      if (useBroker)
        gw->SetBroker (brokerAddr, BROKER_PORT);
      chs.Get (c)->AddApplication (gw);
      gw->SetStartTime (Seconds (0));
      gw->SetStopTime (Seconds (SIM_T));
    }

  // Publishers on sensors
  Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable> ();
  rng->SetAttribute ("Min", DoubleValue (5.0));
  rng->SetAttribute ("Max", DoubleValue (20.0));

  uint32_t nECG = (nECGin > 0) ? nECGin : nSens / 3;
  uint32_t nHR  = (nHRin > 0)  ? nHRin  : nSens / 3;
  if (nECG + nHR > nSens) { nECG = nSens / 3; nHR = nSens / 3; }
  // rest = temperature

  for (uint32_t n = 0; n < nSens; n++)
    {
      uint32_t chIf = nSens + cAssign[n];
      Ipv4Address gwAddr = ifaces.GetAddress (chIf);

      uint16_t topic; Time interval; uint32_t payload; uint8_t qos;
      if (n < nECG) {
        topic = TOPIC_ECG; interval = MilliSeconds (250);
        payload = 128; qos = PRIORITY_HIGH;
      } else if (n < nECG + nHR) {
        topic = TOPIC_HEART_RATE; interval = Seconds (1.0);
        payload = 64; qos = PRIORITY_MEDIUM;
      } else {
        topic = TOPIC_TEMPERATURE; interval = Seconds (5.0);
        payload = 32; qos = PRIORITY_LOW;
      }

      Ptr<MqttSnPublisher> pub = CreateObject<MqttSnPublisher> ();
      pub->Setup (gwAddr, MQTT_PORT, topic, interval, payload, qos);
      pub->EnableEmergencyDetection (EMERGENCY_PROB);
      sens.Get (n)->AddApplication (pub);
      pub->SetStartTime (Seconds (rng->GetValue ()));
      pub->SetStopTime (Seconds (SIM_T - 2.0));
    }

  std::cout << "  Sensors: " << nECG << " ECG + " << nHR << " HR + "
            << (nSens - nECG - nHR) << " Temp\n"
            << "  Broker: " << (useBroker ? "enabled" : "disabled") << "\n\n";
}

void PrintResults (Ptr<FlowMonitor> fm, FlowMonitorHelper &fh,
                   NodeContainer &chs, NodeContainer &sink,
                   uint32_t nCH, bool useBroker, std::string csvName)
{
  fm->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> cls = DynamicCast<Ipv4FlowClassifier> (fh.GetClassifier ());
  auto stats = fm->GetFlowStats ();

  uint64_t tTx = 0, tRx = 0, tRxB = 0;
  double tDel = 0; uint32_t fl = 0, dead = 0;

  std::ofstream csv (csvName);
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
    << "  RESULTS\n"
    << "============================================================\n"
    << "  Flows: " << fl << " (dead: " << dead << ")\n"
    << "  Tx: " << tTx << " | Rx: " << tRx << "\n"
    << "  PDR: " << std::fixed << std::setprecision (2) << pdr << "%\n"
    << "  Avg Delay: " << avgD << " ms\n"
    << "  Throughput: " << (tRxB*8.0/SIM_T/1000) << " kbps\n"
    << "  Output: " << csvName << "\n"
    << "============================================================\n\n";

  // Per-Gateway
  uint32_t totalEmerg = 0, totalFwd = 0;
  for (uint32_t c = 0; c < nCH; c++)
    {
      Ptr<MqttSnGateway> gw = DynamicCast<MqttSnGateway> (chs.Get (c)->GetApplication (0));
      if (gw) {
        gw->PrintStats ();
        totalEmerg += gw->GetStats ().emergencies;
        totalFwd += gw->GetStats ().forwardedToBroker;
      }
    }

  if (useBroker)
    {
      Ptr<MqttSnBroker> br = DynamicCast<MqttSnBroker> (sink.Get (0)->GetApplication (0));
      if (br) br->PrintStats ();
    }

  std::cout << "  Emergencies: " << totalEmerg
            << " | Forwarded: " << totalFwd << "\n\n";

  fm->SerializeToXmlFile (csvName + ".flowmon.xml", true, true);
}

// ============================================================
//  MAIN
// ============================================================
int main (int argc, char *argv[])
{
  uint32_t nSensors = 180;
  uint32_t nCH      = 20;
  uint32_t nECGcmd  = 0;   // 0 = auto (nSensors/3)
  uint32_t nHRcmd   = 0;   // 0 = auto (nSensors/3)
  double   simTime  = SIM_T;
  bool     useBroker = true;
  bool     enableAnim = false;
  bool     verbose  = false;
  std::string csvName = "";

  CommandLine cmd (__FILE__);
  cmd.AddValue ("nSensors", "Number of sensor nodes", nSensors);
  cmd.AddValue ("nCH", "Number of cluster heads", nCH);
  cmd.AddValue ("nECG", "Number of ECG sensors (0=auto)", nECGcmd);
  cmd.AddValue ("nHR", "Number of HR sensors (0=auto)", nHRcmd);
  cmd.AddValue ("simTime", "Simulation time", simTime);
  cmd.AddValue ("broker", "Enable broker/sink", useBroker);
  cmd.AddValue ("anim", "Enable NetAnim", enableAnim);
  cmd.AddValue ("verbose", "Verbose logging", verbose);
  cmd.AddValue ("csv", "Output CSV filename", csvName);
  cmd.Parse (argc, argv);

  if (verbose) {
    LogComponentEnable ("ClusterAodvMqtt", LOG_LEVEL_INFO);
    LogComponentEnable ("MqttSnPublisher", LOG_LEVEL_INFO);
    LogComponentEnable ("MqttSnGateway", LOG_LEVEL_INFO);
    LogComponentEnable ("MqttSnBroker", LOG_LEVEL_INFO);
  }

  // Auto CSV name
  if (csvName.empty ())
    {
      std::ostringstream oss;
      oss << "mqtt-sn-" << nSensors << "nodes";
      if (useBroker) oss << "-broker";
      oss << "-results.csv";
      csvName = oss.str ();
    }

  uint32_t totalNodes = nSensors + nCH + (useBroker ? 1 : 0);

  SeedManager::SetSeed (42); SeedManager::SetRun (1);

  std::cout << "\n============================================================\n"
    << "  MQTT-SN MIoT Simulation\n"
    << "  Sensors: " << nSensors << " | CHs: " << nCH
    << " | Broker: " << (useBroker ? "yes" : "no")
    << " | Total: " << totalNodes << "\n"
    << "  Area: " << AREA << "x" << AREA << "m | AODV | " << simTime << "s\n"
    << "  CSV: " << csvName << "\n"
    << "============================================================\n\n";

  // Build
  NodeContainer sens, chs, sink, all;
  sens.Create (nSensors);
  chs.Create (nCH);
  if (useBroker) sink.Create (1);
  all.Add (sens); all.Add (chs);
  if (useBroker) all.Add (sink);

  YansWifiPhyHelper phy;
  NetDeviceContainer dev = ConfigWifi (all, phy);
  Ipv4InterfaceContainer ifaces = InstallStack (all, dev);

  if (useBroker)
    PositionNodes (sens, chs, sink, nCH);
  else
    {
      // Position without sink
      MobilityHelper m; m.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
      uint32_t cols = (uint32_t)std::ceil (std::sqrt ((double)nCH));
      if (cols < 1) cols = 1;
      uint32_t rows = (nCH + cols - 1) / cols;
      Ptr<ListPositionAllocator> cp = CreateObject<ListPositionAllocator> ();
      double cW = AREA/cols, cH = AREA/rows;
      for (uint32_t i = 0; i < nCH; i++)
        cp->Add (Vector ((i%cols+0.5)*cW, (i/cols+0.5)*cH, 0));
      m.SetPositionAllocator (cp); m.Install (chs);

      Ptr<ListPositionAllocator> sp = CreateObject<ListPositionAllocator> ();
      Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable> ();
      rx->SetAttribute ("Min", DoubleValue (0)); rx->SetAttribute ("Max", DoubleValue (AREA));
      Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable> ();
      ry->SetAttribute ("Min", DoubleValue (0)); ry->SetAttribute ("Max", DoubleValue (AREA));
      for (uint32_t i = 0; i < nSensors; i++)
        sp->Add (Vector (rx->GetValue (), ry->GetValue (), 0));
      m.SetPositionAllocator (sp); m.Install (sens);
    }

  AssignClusters (sens, chs, nCH);
  InstallMqtt (sens, chs, sink, ifaces, nSensors, nCH, useBroker, nECGcmd, nHRcmd);

  FlowMonitorHelper fh;
  Ptr<FlowMonitor> fm = fh.InstallAll ();

  // NetAnim
  AnimationInterface *anim = nullptr;
  if (enableAnim)
    {
      anim = new AnimationInterface ("mqtt-sn-animation.xml");
      anim->SetMaxPktsPerTraceFile (500000);
      uint32_t nECG = nSensors/3, nHR = nSensors/3;
      for (uint32_t i = 0; i < nECG; i++) {
        anim->UpdateNodeColor (sens.Get (i), 255, 59, 48);
        anim->UpdateNodeSize (sens.Get (i)->GetId (), 8, 8); }
      for (uint32_t i = nECG; i < nECG+nHR; i++) {
        anim->UpdateNodeColor (sens.Get (i), 0, 122, 255);
        anim->UpdateNodeSize (sens.Get (i)->GetId (), 8, 8); }
      for (uint32_t i = nECG+nHR; i < nSensors; i++) {
        anim->UpdateNodeColor (sens.Get (i), 52, 199, 89);
        anim->UpdateNodeSize (sens.Get (i)->GetId (), 8, 8); }
      for (uint32_t i = 0; i < nCH; i++) {
        anim->UpdateNodeColor (chs.Get (i), 175, 82, 222);
        anim->UpdateNodeSize (chs.Get (i)->GetId (), 25, 25); }
      if (useBroker) {
        anim->UpdateNodeColor (sink.Get (0), 255, 204, 0);
        anim->UpdateNodeSize (sink.Get (0)->GetId (), 40, 40); }
    }

  std::cout << "[RUN] " << simTime << "s...\n";
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  PrintResults (fm, fh, chs, sink, nCH, useBroker, csvName);

  Simulator::Destroy ();
  if (anim) delete anim;
  std::cout << "[DONE]\n\n";
  return 0;
}
