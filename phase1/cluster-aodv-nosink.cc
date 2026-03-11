/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Traditional WSN: Cluster-Based AODV + UDP (Scalability Version)
 * ================================================================
 * Supports command-line node count:
 *   ./ns3 run "cluster-aodv-nosink --numRegular=50 --numCH=5"
 *   ./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20"
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

NS_LOG_COMPONENT_DEFINE ("ClusterAodvNoSink");

static const double   AREA       = 1000.0;
static const double   SIM_TIME   = 100.0;
static const uint32_t PKT_SIZE   = 512;
static const std::string DATA_RATE = "4kbps";
static const uint16_t APP_PORT   = 9;
static const double   START_MIN  = 5.0;
static const double   START_MAX  = 20.0;
static const double   STOP_TIME  = 95.0;

// Dynamic (sized at runtime)
std::vector<uint32_t> clusterAssign;
std::vector<uint32_t> clusterSizes;

static double CalcDist (const Vector &a, const Vector &b)
{ return std::sqrt ((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y)); }

// ============================================================
NetDeviceContainer
ConfigWifi (NodeContainer &all, YansWifiPhyHelper &phy)
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

Ipv4InterfaceContainer
InstallStack (NodeContainer &all, NetDeviceContainer &dev)
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

void PositionNodes (NodeContainer &sens, NodeContainer &chs, uint32_t nCH)
{
  MobilityHelper m; m.SetMobilityModel ("ns3::ConstantPositionMobilityModel");

  uint32_t cols = (uint32_t)std::ceil (std::sqrt ((double)nCH));
  if (cols < 1) cols = 1;
  uint32_t rows = (nCH + cols - 1) / cols;

  Ptr<ListPositionAllocator> cp = CreateObject<ListPositionAllocator> ();
  double cW = AREA / cols, cH = AREA / rows;
  for (uint32_t i = 0; i < nCH; i++)
    cp->Add (Vector ((i%cols+0.5)*cW, (i/cols+0.5)*cH, 0));
  m.SetPositionAllocator (cp); m.Install (chs);

  uint32_t nSens = sens.GetN ();
  Ptr<ListPositionAllocator> sp = CreateObject<ListPositionAllocator> ();
  Ptr<UniformRandomVariable> rx = CreateObject<UniformRandomVariable> ();
  rx->SetAttribute ("Min", DoubleValue (0)); rx->SetAttribute ("Max", DoubleValue (AREA));
  Ptr<UniformRandomVariable> ry = CreateObject<UniformRandomVariable> ();
  ry->SetAttribute ("Min", DoubleValue (0)); ry->SetAttribute ("Max", DoubleValue (AREA));
  for (uint32_t i = 0; i < nSens; i++)
    sp->Add (Vector (rx->GetValue (), ry->GetValue (), 0));
  m.SetPositionAllocator (sp); m.Install (sens);
}

void AssignClusters (NodeContainer &sens, NodeContainer &chs, uint32_t nCH)
{
  uint32_t nSens = sens.GetN ();
  clusterAssign.resize (nSens, 0);
  clusterSizes.resize (nCH, 0);

  std::vector<Vector> chP (nCH);
  for (uint32_t i = 0; i < nCH; i++)
    chP[i] = chs.Get (i)->GetObject<MobilityModel> ()->GetPosition ();
  std::fill (clusterSizes.begin (), clusterSizes.end (), 0);

  for (uint32_t n = 0; n < nSens; n++)
    {
      Vector np = sens.Get (n)->GetObject<MobilityModel> ()->GetPosition ();
      double md = 1e9; uint32_t ne = 0;
      for (uint32_t c = 0; c < nCH; c++)
        { double d = CalcDist (np, chP[c]); if (d < md) { md = d; ne = c; } }
      clusterAssign[n] = ne; clusterSizes[ne]++;
    }

  std::cout << "  Clusters: min=" << *std::min_element (clusterSizes.begin (), clusterSizes.end ())
            << " max=" << *std::max_element (clusterSizes.begin (), clusterSizes.end ())
            << " avg=" << std::fixed << std::setprecision (1)
            << (double)nSens/nCH << "\n";
}

void InstallTraffic (NodeContainer &sens, NodeContainer &chs,
                     Ipv4InterfaceContainer &ifaces, uint32_t nSens)
{
  Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable> ();
  rng->SetAttribute ("Min", DoubleValue (START_MIN));
  rng->SetAttribute ("Max", DoubleValue (START_MAX));

  for (uint32_t n = 0; n < nSens; n++)
    {
      uint32_t chIf = nSens + clusterAssign[n];
      OnOffHelper onoff ("ns3::UdpSocketFactory",
        InetSocketAddress (ifaces.GetAddress (chIf), APP_PORT));
      onoff.SetAttribute ("DataRate", StringValue (DATA_RATE));
      onoff.SetAttribute ("PacketSize", UintegerValue (PKT_SIZE));
      onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
      onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
      ApplicationContainer app = onoff.Install (sens.Get (n));
      app.Start (Seconds (rng->GetValue ()));
      app.Stop (Seconds (STOP_TIME));
    }

  PacketSinkHelper sink ("ns3::UdpSocketFactory",
    InetSocketAddress (Ipv4Address::GetAny (), APP_PORT));
  uint32_t nCH = chs.GetN ();
  for (uint32_t c = 0; c < nCH; c++)
    sink.Install (chs.Get (c)).Start (Seconds (0.0));

  std::cout << "  Traffic: " << nSens << " nodes -> " << nCH
            << " CHs (UDP " << DATA_RATE << ", " << PKT_SIZE << "B)\n\n";
}

void PrintResults (Ptr<FlowMonitor> fm, FlowMonitorHelper &fh,
                   std::string csvName)
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
    << "  WSN RESULTS\n"
    << "============================================================\n"
    << "  Flows: " << fl << " (dead: " << dead << ")\n"
    << "  Tx: " << tTx << " | Rx: " << tRx << "\n"
    << "  PDR: " << std::fixed << std::setprecision (2) << pdr << "%\n"
    << "  Avg Delay: " << avgD << " ms\n"
    << "  Throughput: " << (tRxB*8.0/SIM_TIME/1000) << " kbps\n"
    << "  Output: " << csvName << "\n"
    << "============================================================\n\n";

  fm->SerializeToXmlFile (csvName + ".flowmon.xml", true, true);
}

// ============================================================
int main (int argc, char *argv[])
{
  uint32_t numRegular = 180;
  uint32_t numCH      = 20;
  double   simTime    = SIM_TIME;
  bool     enableAnim = false;
  bool     verbose    = false;
  std::string csvName = "";

  CommandLine cmd (__FILE__);
  cmd.AddValue ("numRegular", "Number of regular sensor nodes", numRegular);
  cmd.AddValue ("numCH", "Number of cluster heads", numCH);
  cmd.AddValue ("simTime", "Simulation time (seconds)", simTime);
  cmd.AddValue ("anim", "Enable NetAnim output", enableAnim);
  cmd.AddValue ("verbose", "Enable verbose logging", verbose);
  cmd.AddValue ("csv", "Output CSV filename", csvName);
  cmd.Parse (argc, argv);

  if (verbose)
    LogComponentEnable ("ClusterAodvNoSink", LOG_LEVEL_INFO);

  // Auto CSV name
  if (csvName.empty ())
    {
      std::ostringstream oss;
      oss << "wsn-" << numRegular << "nodes-results.csv";
      csvName = oss.str ();
    }

  SeedManager::SetSeed (42);
  SeedManager::SetRun (1);

  std::cout << "\n============================================================\n"
    << "  Traditional WSN (AODV + UDP)\n"
    << "  Sensors: " << numRegular << " | CHs: " << numCH
    << " | Total: " << (numRegular + numCH) << "\n"
    << "  Area: " << AREA << "x" << AREA << "m | AODV | " << simTime << "s\n"
    << "  CSV: " << csvName << "\n"
    << "============================================================\n\n";

  // Build using COMMAND LINE values (not constants!)
  NodeContainer sens, chs, all;
  sens.Create (numRegular);
  chs.Create (numCH);
  all.Add (sens); all.Add (chs);

  YansWifiPhyHelper phy;
  NetDeviceContainer dev = ConfigWifi (all, phy);
  Ipv4InterfaceContainer ifaces = InstallStack (all, dev);

  PositionNodes (sens, chs, numCH);
  AssignClusters (sens, chs, numCH);
  InstallTraffic (sens, chs, ifaces, numRegular);

  FlowMonitorHelper fh;
  Ptr<FlowMonitor> fm = fh.InstallAll ();

  std::cout << "[RUN] " << simTime << "s...\n";
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  PrintResults (fm, fh, csvName);

  Simulator::Destroy ();
  std::cout << "[DONE]\n\n";
  return 0;
}
