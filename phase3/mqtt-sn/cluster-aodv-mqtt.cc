/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Priority-Aware MQTT-SN for MIoT (Phase 3)
 * ============================================
 * 200 Nodes | 20 CH | AODV | MQTT-SN with Priority Queue
 *
 * Priority System:
 *   CRITICAL (3): Emergency alerts (abnormal sensor values)
 *   HIGH     (2): ECG data (250ms, must deliver)
 *   MEDIUM   (1): Heart Rate (1s, important)
 *   LOW      (0): Temperature (5s, best effort)
 *
 * Build:
 *   cp *.h *.cc ~/ns-3-dev/scratch/cluster-aodv-mqtt/
 *   cd ~/ns-3-dev && ./ns3 build
 *   ./ns3 run cluster-aodv-mqtt
 */

#include "mqtt-sn-header.h"
#include "mqtt-sn-publisher.h"
#include "mqtt-sn-gateway.h"

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
static const uint32_t N_REG  = N_ECG + N_HR + N_TEMP;
static const uint32_t N_CH   = 20;
static const uint32_t N_TOT  = N_REG + N_CH;
static const double   AREA   = 1000.0;
static const uint32_t COLS   = 5, ROWS = 4;
static const double   SIM_T  = 100.0;
static const uint16_t PORT   = 1883;
static const double   EMERGENCY_PROB = 0.005; // 0.5% chance per publish

std::vector<uint32_t> cAssign (N_REG, 0);
std::vector<uint32_t> cSizes (N_CH, 0);

static double CalcDist (const Vector &a, const Vector &b)
{ return std::sqrt ((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y)); }

void CreateNodes (NodeContainer &s, NodeContainer &ch, NodeContainer &all)
{ s.Create(N_REG); ch.Create(N_CH); all.Add(s); all.Add(ch); }

NetDeviceContainer ConfigWifi (NodeContainer &all, YansWifiPhyHelper &phy)
{
  WifiHelper w; w.SetStandard (WIFI_STANDARD_80211b);
  w.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
    "DataMode", StringValue("DsssRate11Mbps"), "ControlMode", StringValue("DsssRate1Mbps"));
  YansWifiChannelHelper ch;
  ch.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  ch.AddPropagationLoss ("ns3::LogDistancePropagationLossModel",
    "Exponent", DoubleValue(2.5), "ReferenceDistance", DoubleValue(1.0), "ReferenceLoss", DoubleValue(46.6777));
  phy.SetChannel (ch.Create());
  phy.Set ("TxPowerStart", DoubleValue(20.0));
  phy.Set ("TxPowerEnd", DoubleValue(20.0));
  WifiMacHelper mac; mac.SetType ("ns3::AdhocWifiMac");
  return w.Install (phy, mac, all);
}

Ipv4InterfaceContainer InstallStack (NodeContainer &all, NetDeviceContainer &dev)
{
  AodvHelper aodv;
  aodv.Set("HelloInterval", TimeValue(Seconds(2)));
  aodv.Set("AllowedHelloLoss", UintegerValue(3));
  aodv.Set("ActiveRouteTimeout", TimeValue(Seconds(15)));
  aodv.Set("RreqRetries", UintegerValue(5));
  aodv.Set("NetDiameter", UintegerValue(20));
  aodv.Set("NodeTraversalTime", TimeValue(MilliSeconds(100)));
  InternetStackHelper inet; inet.SetRoutingHelper(aodv); inet.Install(all);
  Ipv4AddressHelper addr; addr.SetBase("10.1.0.0","255.255.0.0");
  return addr.Assign(dev);
}

void PositionNodes (NodeContainer &s, NodeContainer &ch)
{
  MobilityHelper m; m.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  Ptr<ListPositionAllocator> cp = CreateObject<ListPositionAllocator>();
  double cW = AREA/COLS, cH = AREA/ROWS;
  for (uint32_t i=0; i<N_CH; i++)
    cp->Add(Vector((i%COLS+0.5)*cW, (i/COLS+0.5)*cH, 0));
  m.SetPositionAllocator(cp); m.Install(ch);

  Ptr<ListPositionAllocator> sp = CreateObject<ListPositionAllocator>();
  Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable>();
  rx->SetAttribute("Min",DoubleValue(0)); rx->SetAttribute("Max",DoubleValue(AREA));
  Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable>();
  ry->SetAttribute("Min",DoubleValue(0)); ry->SetAttribute("Max",DoubleValue(AREA));
  for (uint32_t i=0; i<N_REG; i++) sp->Add(Vector(rx->GetValue(),ry->GetValue(),0));
  m.SetPositionAllocator(sp); m.Install(s);
}

void AssignClusters (NodeContainer &s, NodeContainer &ch)
{
  std::vector<Vector> chP(N_CH);
  for (uint32_t i=0; i<N_CH; i++) chP[i] = ch.Get(i)->GetObject<MobilityModel>()->GetPosition();
  std::fill(cSizes.begin(), cSizes.end(), 0);
  for (uint32_t n=0; n<N_REG; n++) {
    Vector np = s.Get(n)->GetObject<MobilityModel>()->GetPosition();
    double md = 1e9; uint32_t ne = 0;
    for (uint32_t c=0; c<N_CH; c++) { double d=CalcDist(np,chP[c]); if(d<md){md=d;ne=c;} }
    cAssign[n]=ne; cSizes[ne]++;
  }
  std::cout << "  Clusters: min=" << *std::min_element(cSizes.begin(),cSizes.end())
            << " max=" << *std::max_element(cSizes.begin(),cSizes.end())
            << " avg=" << std::fixed << std::setprecision(1) << (double)N_REG/N_CH << "\n";
}

void InstallMqtt (NodeContainer &s, NodeContainer &ch, Ipv4InterfaceContainer &ifaces)
{
  Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable>();
  rng->SetAttribute("Min", DoubleValue(5.0));
  rng->SetAttribute("Max", DoubleValue(20.0));

  // Gateways
  for (uint32_t c=0; c<N_CH; c++) {
    Ptr<MqttSnGateway> gw = CreateObject<MqttSnGateway>();
    gw->Setup(PORT);
    ch.Get(c)->AddApplication(gw);
    gw->SetStartTime(Seconds(0)); gw->SetStopTime(Seconds(SIM_T));
  }

  // Sensors with priority
  uint32_t ecg=0, hr=0, tmp=0;
  for (uint32_t n=0; n<N_REG; n++) {
    uint32_t chIf = N_REG + cAssign[n];
    Ipv4Address gwAddr = ifaces.GetAddress(chIf);

    uint16_t topic; Time interval; uint32_t payload; uint8_t qos;

    if (n < N_ECG) {
      topic = TOPIC_ECG; interval = MilliSeconds(250);
      payload = 128; qos = PRIORITY_HIGH; ecg++;
    } else if (n < N_ECG + N_HR) {
      topic = TOPIC_HEART_RATE; interval = Seconds(1.0);
      payload = 64; qos = PRIORITY_MEDIUM; hr++;
    } else {
      topic = TOPIC_TEMPERATURE; interval = Seconds(5.0);
      payload = 32; qos = PRIORITY_LOW; tmp++;
    }

    Ptr<MqttSnPublisher> pub = CreateObject<MqttSnPublisher>();
    pub->Setup(gwAddr, PORT, topic, interval, payload, qos);
    pub->EnableEmergencyDetection(EMERGENCY_PROB);
    s.Get(n)->AddApplication(pub);
    pub->SetStartTime(Seconds(rng->GetValue()));
    pub->SetStopTime(Seconds(SIM_T - 2.0));
  }

  std::cout << "\n  MQTT-SN Priority Configuration:\n"
            << "    ECG:         " << ecg << " nodes | QoS=2 (HIGH)     | 250ms | 128B\n"
            << "    Heart Rate:  " << hr  << " nodes | QoS=1 (MEDIUM)   | 1s    | 64B\n"
            << "    Temperature: " << tmp << " nodes | QoS=0 (LOW)      | 5s    | 32B\n"
            << "    Emergency:   " << std::fixed << std::setprecision(1)
            << (EMERGENCY_PROB*100) << "% chance per publish (CRITICAL)\n\n";
}

void PrintResults (Ptr<FlowMonitor> fm, FlowMonitorHelper &fh, NodeContainer &ch)
{
  fm->CheckForLostPackets();
  Ptr<Ipv4FlowClassifier> cls = DynamicCast<Ipv4FlowClassifier>(fh.GetClassifier());
  auto stats = fm->GetFlowStats();

  uint64_t tTx=0, tRx=0, tRxB=0; double tDel=0; uint32_t fl=0, dead=0;

  std::ofstream csv("mqtt-sn-priority-results.csv");
  csv << "FlowID,SrcAddr,DstAddr,TxPackets,RxPackets,LostPackets,"
      << "PDR_pct,Throughput_kbps,AvgDelay_ms,AvgJitter_ms\n";

  for (auto &kv : stats) {
    auto ft = cls->FindFlow(kv.first); auto &s = kv.second;
    double pdr = s.txPackets>0 ? (double)s.rxPackets/s.txPackets*100 : 0;
    double dur = s.rxPackets>0 ? (s.timeLastRxPacket-s.timeFirstTxPacket).GetSeconds() : 0;
    double tp = dur>0 ? s.rxBytes*8.0/dur/1000 : 0;
    double dl = s.rxPackets>0 ? s.delaySum.GetMilliSeconds()/(double)s.rxPackets : 0;
    double jt = s.rxPackets>1 ? s.jitterSum.GetMilliSeconds()/(double)(s.rxPackets-1) : 0;
    tTx+=s.txPackets; tRx+=s.rxPackets; tRxB+=s.rxBytes;
    tDel += s.rxPackets>0 ? s.delaySum.GetMilliSeconds() : 0;
    fl++; if(s.rxPackets==0) dead++;
    csv << kv.first << "," << ft.sourceAddress << "," << ft.destinationAddress
        << "," << s.txPackets << "," << s.rxPackets << "," << s.lostPackets
        << "," << std::fixed << std::setprecision(2)
        << pdr << "," << tp << "," << dl << "," << jt << "\n";
  }
  csv.close();

  double pdr = tTx>0 ? (double)tRx/tTx*100 : 0;
  double avgD = tRx>0 ? tDel/tRx : 0;

  std::cout << "============================================================\n"
    << "  PRIORITY-AWARE MQTT-SN RESULTS\n"
    << "============================================================\n"
    << "  Flows: " << fl << " (dead: " << dead << ")\n"
    << "  Tx: " << tTx << " | Rx: " << tRx << "\n"
    << "  PDR: " << std::fixed << std::setprecision(2) << pdr << "%\n"
    << "  Avg Delay: " << avgD << " ms\n"
    << "  Throughput: " << (tRxB*8.0/SIM_T/1000) << " kbps\n"
    << "============================================================\n\n"
    << "  Per-Gateway Statistics (Priority Queue):\n"
    << "  -----------------------------------------\n";

  uint32_t totalEmerg = 0;
  for (uint32_t c=0; c<N_CH; c++) {
    Ptr<MqttSnGateway> gw = DynamicCast<MqttSnGateway>(ch.Get(c)->GetApplication(0));
    if (gw) { gw->PrintStats(); totalEmerg += gw->GetStats().emergencies; }
  }
  std::cout << "\n  Total Emergencies: " << totalEmerg << "\n";
  std::cout << "  Output: mqtt-sn-priority-results.csv\n"
            << "============================================================\n\n";

  fm->SerializeToXmlFile("mqtt-sn-priority-flowmon.xml", true, true);
}

int main (int argc, char *argv[])
{
  double simTime = SIM_T;
  bool enableAnim = true, verbose = false;

  CommandLine cmd(__FILE__);
  cmd.AddValue("simTime","Sim time",simTime);
  cmd.AddValue("anim","NetAnim",enableAnim);
  cmd.AddValue("verbose","Verbose",verbose);
  cmd.Parse(argc,argv);

  if (verbose) {
    LogComponentEnable("ClusterAodvMqtt", LOG_LEVEL_INFO);
    LogComponentEnable("MqttSnPublisher", LOG_LEVEL_INFO);
    LogComponentEnable("MqttSnGateway", LOG_LEVEL_INFO);
  }

  SeedManager::SetSeed(42); SeedManager::SetRun(1);

  std::cout << "\n============================================================\n"
    << "  PRIORITY-AWARE MQTT-SN for MIoT (Phase 3)\n"
    << "  Sensors: " << N_REG << " (" << N_ECG << " ECG + "
    << N_HR << " HR + " << N_TEMP << " Temp)\n"
    << "  Gateways: " << N_CH << " | Total: " << N_TOT
    << " | AODV | " << simTime << "s\n"
    << "  Priority: ECG=HIGH, HR=MEDIUM, Temp=LOW, Emergency=CRITICAL\n"
    << "============================================================\n\n";

  NodeContainer sens, chs, all;
  CreateNodes(sens, chs, all);
  YansWifiPhyHelper phy;
  NetDeviceContainer dev = ConfigWifi(all, phy);
  Ipv4InterfaceContainer ifaces = InstallStack(all, dev);
  PositionNodes(sens, chs);
  AssignClusters(sens, chs);
  InstallMqtt(sens, chs, ifaces);

  FlowMonitorHelper fh;
  Ptr<FlowMonitor> fm = fh.InstallAll();

  AnimationInterface *anim = nullptr;
  if (enableAnim) {
    anim = new AnimationInterface("mqtt-sn-priority-animation.xml");
    anim->SetMaxPktsPerTraceFile(500000);
    // ECG = Red (critical)
    for (uint32_t i=0; i<N_ECG; i++) {
      anim->UpdateNodeDescription(sens.Get(i), "ECG[H]");
      anim->UpdateNodeColor(sens.Get(i), 255, 59, 48);
      anim->UpdateNodeSize(sens.Get(i)->GetId(), 8, 8);
    }
    // HR = Blue (medium)
    for (uint32_t i=N_ECG; i<N_ECG+N_HR; i++) {
      anim->UpdateNodeDescription(sens.Get(i), "HR[M]");
      anim->UpdateNodeColor(sens.Get(i), 0, 122, 255);
      anim->UpdateNodeSize(sens.Get(i)->GetId(), 8, 8);
    }
    // Temp = Green (low)
    for (uint32_t i=N_ECG+N_HR; i<N_REG; i++) {
      anim->UpdateNodeDescription(sens.Get(i), "Tmp[L]");
      anim->UpdateNodeColor(sens.Get(i), 52, 199, 89);
      anim->UpdateNodeSize(sens.Get(i)->GetId(), 8, 8);
    }
    // Gateways
    for (uint32_t i=0; i<N_CH; i++) {
      anim->UpdateNodeDescription(chs.Get(i),
        "GW"+std::to_string(i)+"["+std::to_string(cSizes[i])+"]");
      anim->UpdateNodeColor(chs.Get(i), 175, 82, 222);
      anim->UpdateNodeSize(chs.Get(i)->GetId(), 25, 25);
    }
  }

  std::cout << "[RUN] Simulating " << simTime << "s...\n";
  Simulator::Stop(Seconds(simTime));
  Simulator::Run();
  PrintResults(fm, fh, chs);
  Simulator::Destroy();
  if (anim) delete anim;
  std::cout << "[DONE]\n\n";
  return 0;
}
