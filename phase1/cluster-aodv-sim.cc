/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Cluster-Based AODV with Sink Node
 * ===================================
 * 200 Nodes | 20 CH | 1 Sink | AODV
 *
 * Tier-1: [180 Sensors] --UDP--> [20 CHs]
 * Tier-2: [20 CHs]      --UDP--> [1 Sink]
 *
 * Build:
 *   cp cluster-aodv-sim.cc ~/ns-3-dev/scratch/
 *   cd ~/ns-3-dev && ./ns3 build
 *   ./ns3 run cluster-aodv-sim
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/aodv-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"

#include <cmath>
#include <vector>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <algorithm>
#include <limits>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("ClusterAodvSink");

static const uint32_t N_REG  = 180;
static const uint32_t N_CH   = 20;
static const uint32_t N_SINK = 1;
static const uint32_t N_TOT  = N_REG + N_CH + N_SINK; // 201

static const double   AREA   = 1000.0;
static const uint32_t COLS   = 5, ROWS = 4;
static const double   SIM_T  = 100.0;

static const uint32_t T1_PKT = 512;
static const std::string T1_RATE = "4kbps";
static const uint32_t T2_PKT = 1024;

static const uint16_t T1_PORT = 9;
static const uint16_t T2_PORT = 10;

static const double START_MIN = 5.0, START_MAX = 20.0;
static const double T2_START  = 25.0;
static const double STOP      = 95.0;

std::vector<uint32_t> cAssign (N_REG, 0);
std::vector<uint32_t> cSizes (N_CH, 0);

static double CalcDist (const Vector &a, const Vector &b)
{
  return std::sqrt ((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y));
}

// Step 1: Create 201 Nodes
void CreateNodes (NodeContainer &reg, NodeContainer &ch, NodeContainer &sink, NodeContainer &all)
{
  reg.Create (N_REG);
  ch.Create (N_CH);
  sink.Create (N_SINK);
  all.Add (reg); all.Add (ch); all.Add (sink);
}

// Step 2: WiFi
NetDeviceContainer ConfigWifi (NodeContainer &all, YansWifiPhyHelper &phy)
{
  WifiHelper w;
  w.SetStandard (WIFI_STANDARD_80211b);
  w.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
    "DataMode", StringValue ("DsssRate11Mbps"),
    "ControlMode", StringValue ("DsssRate1Mbps"));

  YansWifiChannelHelper ch;
  ch.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  ch.AddPropagationLoss ("ns3::LogDistancePropagationLossModel",
    "Exponent", DoubleValue (2.5),
    "ReferenceDistance", DoubleValue (1.0),
    "ReferenceLoss", DoubleValue (46.6777));
  phy.SetChannel (ch.Create ());
  phy.Set ("TxPowerStart", DoubleValue (20.0));
  phy.Set ("TxPowerEnd", DoubleValue (20.0));

  WifiMacHelper mac;
  mac.SetType ("ns3::AdhocWifiMac");
  return w.Install (phy, mac, all);
}

// Step 3: AODV + IP
Ipv4InterfaceContainer InstallStack (NodeContainer &all, NetDeviceContainer &dev)
{
  AodvHelper aodv;
  aodv.Set ("HelloInterval", TimeValue (Seconds (2)));
  aodv.Set ("AllowedHelloLoss", UintegerValue (3));
  aodv.Set ("ActiveRouteTimeout", TimeValue (Seconds (15)));
  aodv.Set ("RreqRetries", UintegerValue (5));
  aodv.Set ("NetDiameter", UintegerValue (20));
  aodv.Set ("NodeTraversalTime", TimeValue (MilliSeconds (100)));

  InternetStackHelper inet;
  inet.SetRoutingHelper (aodv);
  inet.Install (all);

  Ipv4AddressHelper addr;
  addr.SetBase ("10.1.0.0", "255.255.0.0");
  return addr.Assign (dev);
}

// Step 4: Position
void PositionNodes (NodeContainer &reg, NodeContainer &ch, NodeContainer &sink)
{
  MobilityHelper mob;
  mob.SetMobilityModel ("ns3::ConstantPositionMobilityModel");

  // CHs: 4x5 grid
  Ptr<ListPositionAllocator> cp = CreateObject<ListPositionAllocator> ();
  double cW = AREA / COLS, cH = AREA / ROWS;
  for (uint32_t i = 0; i < N_CH; i++)
    cp->Add (Vector ((i%COLS+0.5)*cW, (i/COLS+0.5)*cH, 0));
  mob.SetPositionAllocator (cp);
  mob.Install (ch);

  // Regular: random
  Ptr<ListPositionAllocator> rp = CreateObject<ListPositionAllocator> ();
  Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable> ();
  rx->SetAttribute ("Min", DoubleValue (0)); rx->SetAttribute ("Max", DoubleValue (AREA));
  Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable> ();
  ry->SetAttribute ("Min", DoubleValue (0)); ry->SetAttribute ("Max", DoubleValue (AREA));
  for (uint32_t i = 0; i < N_REG; i++)
    rp->Add (Vector (rx->GetValue (), ry->GetValue (), 0));
  mob.SetPositionAllocator (rp);
  mob.Install (reg);

  // Sink: center
  Ptr<ListPositionAllocator> sp = CreateObject<ListPositionAllocator> ();
  sp->Add (Vector (AREA/2, AREA/2, 0));
  mob.SetPositionAllocator (sp);
  mob.Install (sink);
}

// Step 5: Cluster Assignment
void AssignClusters (NodeContainer &reg, NodeContainer &ch)
{
  std::vector<Vector> chP (N_CH);
  for (uint32_t i = 0; i < N_CH; i++)
    chP[i] = ch.Get(i)->GetObject<MobilityModel>()->GetPosition ();

  std::fill (cSizes.begin(), cSizes.end(), 0);
  for (uint32_t n = 0; n < N_REG; n++)
    {
      Vector np = reg.Get(n)->GetObject<MobilityModel>()->GetPosition ();
      double md = std::numeric_limits<double>::max ();
      uint32_t ne = 0;
      for (uint32_t c = 0; c < N_CH; c++)
        { double d = CalcDist(np, chP[c]); if (d < md) { md = d; ne = c; } }
      cAssign[n] = ne;
      cSizes[ne]++;
    }

  std::cout << "  Clusters: min=" << *std::min_element(cSizes.begin(), cSizes.end())
            << " max=" << *std::max_element(cSizes.begin(), cSizes.end())
            << " avg=" << std::fixed << std::setprecision(1) << (double)N_REG/N_CH << "\n";
}

// Step 6: Traffic (2-Tier)
void InstallTraffic (NodeContainer &reg, NodeContainer &ch, NodeContainer &sink,
                     Ipv4InterfaceContainer &ifaces)
{
  Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable> ();
  rng->SetAttribute ("Min", DoubleValue (START_MIN));
  rng->SetAttribute ("Max", DoubleValue (START_MAX));

  // Tier 1: Node -> CH
  for (uint32_t n = 0; n < N_REG; n++)
    {
      uint32_t chIf = N_REG + cAssign[n];
      OnOffHelper onoff ("ns3::UdpSocketFactory",
        InetSocketAddress (ifaces.GetAddress (chIf), T1_PORT));
      onoff.SetAttribute ("DataRate", StringValue (T1_RATE));
      onoff.SetAttribute ("PacketSize", UintegerValue (T1_PKT));
      onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
      onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
      ApplicationContainer app = onoff.Install (reg.Get(n));
      app.Start (Seconds (rng->GetValue ()));
      app.Stop (Seconds (STOP));
    }

  // PacketSink on CHs
  PacketSinkHelper t1s ("ns3::UdpSocketFactory",
    InetSocketAddress (Ipv4Address::GetAny(), T1_PORT));
  for (uint32_t c = 0; c < N_CH; c++)
    t1s.Install (ch.Get(c)).Start (Seconds (0));

  // Tier 2: CH -> Sink (aggregated)
  double compression = 0.3;
  uint32_t sinkIf = N_REG + N_CH; // index 200

  for (uint32_t c = 0; c < N_CH; c++)
    {
      double rate = std::max (1.0, cSizes[c] * 4.0 * compression);
      std::ostringstream rs;
      rs << std::fixed << std::setprecision(0) << rate << "kbps";

      OnOffHelper onoff ("ns3::UdpSocketFactory",
        InetSocketAddress (ifaces.GetAddress (sinkIf), T2_PORT));
      onoff.SetAttribute ("DataRate", StringValue (rs.str()));
      onoff.SetAttribute ("PacketSize", UintegerValue (T2_PKT));
      onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
      onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
      ApplicationContainer app = onoff.Install (ch.Get(c));
      app.Start (Seconds (T2_START));
      app.Stop (Seconds (STOP));
    }

  // PacketSink on Sink
  PacketSinkHelper t2s ("ns3::UdpSocketFactory",
    InetSocketAddress (Ipv4Address::GetAny(), T2_PORT));
  t2s.Install (sink.Get(0)).Start (Seconds (0));

  std::cout << "  Traffic: 180 Tier-1 (4kbps) + 20 Tier-2 (aggregated) -> Sink\n\n";
}

// Step 7: Results
void PrintResults (Ptr<FlowMonitor> fm, FlowMonitorHelper &fh)
{
  fm->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> cls = DynamicCast<Ipv4FlowClassifier>(fh.GetClassifier());
  auto stats = fm->GetFlowStats ();

  uint64_t tTx=0, tRx=0, tRxB=0; double tDel=0; uint32_t fl=0, dead=0;

  std::ofstream csv ("cluster-aodv-sink-results.csv");
  csv << "FlowID,SrcAddr,DstAddr,TxPackets,RxPackets,LostPackets,"
      << "PDR_pct,Throughput_kbps,AvgDelay_ms,AvgJitter_ms\n";

  for (auto &kv : stats)
    {
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
    << "  RESULTS (With Sink)\n"
    << "============================================================\n"
    << "  Flows: " << fl << " (dead: " << dead << ")\n"
    << "  Tx: " << tTx << " | Rx: " << tRx << "\n"
    << "  PDR: " << std::fixed << std::setprecision(2) << pdr << "%\n"
    << "  Avg Delay: " << avgD << " ms\n"
    << "  Throughput: " << (tRxB*8.0/SIM_T/1000) << " kbps\n"
    << "  Output: cluster-aodv-sink-results.csv\n"
    << "============================================================\n\n";

  fm->SerializeToXmlFile ("cluster-aodv-sink-flowmon.xml", true, true);
}

// Main
int main (int argc, char *argv[])
{
  double simTime = SIM_T;
  bool enableAnim = true, verbose = false;

  CommandLine cmd (__FILE__);
  cmd.AddValue ("simTime", "Sim time", simTime);
  cmd.AddValue ("anim", "NetAnim", enableAnim);
  cmd.AddValue ("verbose", "Verbose", verbose);
  cmd.Parse (argc, argv);

  if (verbose) LogComponentEnable ("ClusterAodvSink", LOG_LEVEL_INFO);

  SeedManager::SetSeed (42);
  SeedManager::SetRun (1);

  std::cout << "\n============================================================\n"
    << "  CLUSTER-BASED AODV (With Sink)\n"
    << "  Nodes: " << N_REG << " + " << N_CH << " CH + 1 Sink = " << N_TOT << "\n"
    << "  Area: " << AREA << "x" << AREA << "m | AODV | " << simTime << "s\n"
    << "============================================================\n\n";

  NodeContainer reg, ch, sink, all;
  CreateNodes (reg, ch, sink, all);

  YansWifiPhyHelper phy;
  NetDeviceContainer dev = ConfigWifi (all, phy);
  Ipv4InterfaceContainer ifaces = InstallStack (all, dev);

  PositionNodes (reg, ch, sink);
  AssignClusters (reg, ch);
  InstallTraffic (reg, ch, sink, ifaces);

  FlowMonitorHelper fh;
  Ptr<FlowMonitor> fm = fh.InstallAll ();

  AnimationInterface *anim = nullptr;
  if (enableAnim)
    {
      anim = new AnimationInterface ("cluster-aodv-sink-animation.xml");
      anim->SetMaxPktsPerTraceFile (500000);
      for (uint32_t i = 0; i < N_REG; i++)
        { anim->UpdateNodeColor (reg.Get(i), 100, 149, 237);
          anim->UpdateNodeSize (reg.Get(i)->GetId(), 10, 10); }
      for (uint32_t i = 0; i < N_CH; i++)
        { anim->UpdateNodeDescription (ch.Get(i), "CH" + std::to_string(i) + "[" + std::to_string(cSizes[i]) + "]");
          anim->UpdateNodeColor (ch.Get(i), 220, 20, 60);
          anim->UpdateNodeSize (ch.Get(i)->GetId(), 25, 25); }
      anim->UpdateNodeDescription (sink.Get(0), "SINK");
      anim->UpdateNodeColor (sink.Get(0), 34, 139, 34);
      anim->UpdateNodeSize (sink.Get(0)->GetId(), 35, 35);
    }

  std::cout << "[RUN] Simulating " << simTime << "s...\n";
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();
  PrintResults (fm, fh);
  Simulator::Destroy ();
  if (anim) delete anim;
  std::cout << "[DONE]\n\n";
  return 0;
}
