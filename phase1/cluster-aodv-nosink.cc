/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Cluster-Based AODV Network Traffic Simulation (No Sink)
 * ========================================================
 * 200 Nodes | 20 Cluster Heads | Node Join | Network Traffic
 * ns-3-dev
 *
 * Author : Amro Baseet
 * Date   : March 2026
 * Supervisor: Doç. Dr. İsmail Bütün
 *
 * Description:
 *   180 regular nodes join 20 Cluster Heads based on proximity.
 *   Each node sends periodic sensor data to its assigned CH.
 *   AODV routing discovers paths in the wireless ad-hoc network.
 *
 * Architecture:
 *   [180 Regular Nodes] --UDP 4kbps--> [20 Cluster Heads]
 *
 * Build & Run:
 *   cp cluster-aodv-nosink.cc ~/ns-3-dev/scratch/
 *   cd ~/ns-3-dev && ./ns3 build
 *   ./ns3 run scratch/cluster-aodv-nosink
 *
 *   # Small-scale test:
 *   ./ns3 run "scratch/cluster-aodv-nosink --numRegular=40 --numCH=4 --simTime=50"
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

// ============================================================
//  PARAMETERS
// ============================================================
static const uint32_t NUM_REGULAR_NODES = 180;
static const uint32_t NUM_CLUSTER_HEADS = 20;
static const uint32_t TOTAL_NODES       = NUM_REGULAR_NODES + NUM_CLUSTER_HEADS;  // 200

static const double   AREA_WIDTH        = 1000.0;
static const double   AREA_HEIGHT       = 1000.0;

static const uint32_t CH_GRID_COLS      = 5;
static const uint32_t CH_GRID_ROWS      = 4;

static const double   SIM_TIME          = 100.0;
static const uint32_t PKT_SIZE          = 512;
static const std::string DATA_RATE      = "4kbps";
static const uint16_t APP_PORT          = 9;

static const double   START_MIN         = 5.0;
static const double   START_MAX         = 20.0;
static const double   TRAFFIC_STOP      = 95.0;

// ============================================================
//  CLUSTER DATA
// ============================================================
std::vector<uint32_t> clusterAssignment (NUM_REGULAR_NODES, 0);
std::vector<uint32_t> clusterSizes (NUM_CLUSTER_HEADS, 0);

// ============================================================
//  HELPER
// ============================================================
static double
CalcDist (const Vector &a, const Vector &b)
{
  double dx = a.x - b.x;
  double dy = a.y - b.y;
  return std::sqrt (dx * dx + dy * dy);
}

// ============================================================
//  STEP 1: Create 200 Nodes
// ============================================================
void
CreateNodes (NodeContainer &regularNodes,
             NodeContainer &chNodes,
             NodeContainer &allNodes)
{
  regularNodes.Create (NUM_REGULAR_NODES);
  chNodes.Create (NUM_CLUSTER_HEADS);

  // Order: regular(0-179), CH(180-199)
  allNodes.Add (regularNodes);
  allNodes.Add (chNodes);

  NS_LOG_INFO ("Created " << TOTAL_NODES << " nodes: "
               << NUM_REGULAR_NODES << " regular + "
               << NUM_CLUSTER_HEADS << " CH");
}

// ============================================================
//  STEP 2: Configure WiFi Ad-Hoc
// ============================================================
NetDeviceContainer
ConfigureWifi (NodeContainer &allNodes, YansWifiPhyHelper &wifiPhy, bool enablePcap)
{
  WifiHelper wifi;
  wifi.SetStandard (WIFI_STANDARD_80211b);
  wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                "DataMode", StringValue ("DsssRate11Mbps"),
                                "ControlMode", StringValue ("DsssRate1Mbps"));

  YansWifiChannelHelper wifiChannel;
  wifiChannel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  wifiChannel.AddPropagationLoss ("ns3::LogDistancePropagationLossModel",
                                  "Exponent", DoubleValue (2.5),
                                  "ReferenceDistance", DoubleValue (1.0),
                                  "ReferenceLoss", DoubleValue (46.6777));
  wifiPhy.SetChannel (wifiChannel.Create ());
  wifiPhy.Set ("TxPowerStart", DoubleValue (20.0));
  wifiPhy.Set ("TxPowerEnd", DoubleValue (20.0));

  WifiMacHelper wifiMac;
  wifiMac.SetType ("ns3::AdhocWifiMac");

  NetDeviceContainer devices = wifi.Install (wifiPhy, wifiMac, allNodes);

  if (enablePcap)
    {
      wifiPhy.EnablePcap ("cluster-aodv-nosink", devices);
    }

  return devices;
}

// ============================================================
//  STEP 3: Install AODV + IPv4
// ============================================================
Ipv4InterfaceContainer
InstallInternetStack (NodeContainer &allNodes, NetDeviceContainer &devices)
{
  AodvHelper aodv;
  aodv.Set ("HelloInterval", TimeValue (Seconds (2)));
  aodv.Set ("AllowedHelloLoss", UintegerValue (3));
  aodv.Set ("ActiveRouteTimeout", TimeValue (Seconds (15)));
  aodv.Set ("RreqRetries", UintegerValue (5));
  aodv.Set ("NetDiameter", UintegerValue (20));
  aodv.Set ("NodeTraversalTime", TimeValue (MilliSeconds (100)));

  InternetStackHelper internet;
  internet.SetRoutingHelper (aodv);
  internet.Install (allNodes);

  Ipv4AddressHelper address;
  address.SetBase ("10.1.0.0", "255.255.0.0");
  Ipv4InterfaceContainer interfaces = address.Assign (devices);

  return interfaces;
}

// ============================================================
//  STEP 4: Position Nodes
// ============================================================
void
PositionNodes (NodeContainer &regularNodes, NodeContainer &chNodes)
{
  MobilityHelper mobility;
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");

  // CHs: 4x5 grid
  Ptr<ListPositionAllocator> chPos = CreateObject<ListPositionAllocator> ();
  double cellW = AREA_WIDTH / CH_GRID_COLS;
  double cellH = AREA_HEIGHT / CH_GRID_ROWS;

  for (uint32_t i = 0; i < NUM_CLUSTER_HEADS; i++)
    {
      uint32_t col = i % CH_GRID_COLS;
      uint32_t row = i / CH_GRID_COLS;
      chPos->Add (Vector ((col + 0.5) * cellW, (row + 0.5) * cellH, 0.0));
    }
  mobility.SetPositionAllocator (chPos);
  mobility.Install (chNodes);

  // Regular nodes: random
  Ptr<ListPositionAllocator> nodePos = CreateObject<ListPositionAllocator> ();
  Ptr<UniformRandomVariable> rX = CreateObject<UniformRandomVariable> ();
  rX->SetAttribute ("Min", DoubleValue (0.0));
  rX->SetAttribute ("Max", DoubleValue (AREA_WIDTH));
  Ptr<UniformRandomVariable> rY = CreateObject<UniformRandomVariable> ();
  rY->SetAttribute ("Min", DoubleValue (0.0));
  rY->SetAttribute ("Max", DoubleValue (AREA_HEIGHT));

  for (uint32_t i = 0; i < NUM_REGULAR_NODES; i++)
    {
      nodePos->Add (Vector (rX->GetValue (), rY->GetValue (), 0.0));
    }
  mobility.SetPositionAllocator (nodePos);
  mobility.Install (regularNodes);
}

// ============================================================
//  STEP 5: Assign Nodes to Nearest CH (Node Join)
// ============================================================
void
AssignNodesToClusters (NodeContainer &regularNodes, NodeContainer &chNodes)
{
  std::vector<Vector> chPositions (NUM_CLUSTER_HEADS);
  for (uint32_t i = 0; i < NUM_CLUSTER_HEADS; i++)
    {
      chPositions[i] = chNodes.Get (i)->GetObject<MobilityModel> ()->GetPosition ();
    }

  std::fill (clusterSizes.begin (), clusterSizes.end (), 0);

  for (uint32_t n = 0; n < NUM_REGULAR_NODES; n++)
    {
      Vector np = regularNodes.Get (n)->GetObject<MobilityModel> ()->GetPosition ();
      double minDist = std::numeric_limits<double>::max ();
      uint32_t nearest = 0;

      for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
        {
          double d = CalcDist (np, chPositions[c]);
          if (d < minDist) { minDist = d; nearest = c; }
        }
      clusterAssignment[n] = nearest;
      clusterSizes[nearest]++;
    }

  // Print cluster summary
  uint32_t minS = *std::min_element (clusterSizes.begin (), clusterSizes.end ());
  uint32_t maxS = *std::max_element (clusterSizes.begin (), clusterSizes.end ());

  std::cout << "\n  Cluster Assignment (Node Join):\n"
            << "  --------------------------------\n";
  for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
    {
      std::cout << "    CH" << std::setw (2) << c
                << " (" << std::setw (5) << std::fixed << std::setprecision (0)
                << chPositions[c].x << ", " << std::setw (5) << chPositions[c].y
                << ") -> " << std::setw (2) << clusterSizes[c] << " nodes\n";
    }
  std::cout << "  --------------------------------\n"
            << "  Min: " << minS << " | Max: " << maxS
            << " | Avg: " << std::setprecision (1)
            << (double)NUM_REGULAR_NODES / NUM_CLUSTER_HEADS << "\n\n";
}

// ============================================================
//  STEP 6: Install Traffic (Node -> CH only)
// ============================================================
void
InstallTraffic (NodeContainer &regularNodes,
                NodeContainer &chNodes,
                Ipv4InterfaceContainer &interfaces)
{
  Ptr<UniformRandomVariable> startRng = CreateObject<UniformRandomVariable> ();
  startRng->SetAttribute ("Min", DoubleValue (START_MIN));
  startRng->SetAttribute ("Max", DoubleValue (START_MAX));

  // Each regular node sends UDP to its assigned CH
  for (uint32_t n = 0; n < NUM_REGULAR_NODES; n++)
    {
      uint32_t chIf = NUM_REGULAR_NODES + clusterAssignment[n];  // 180 + chIndex

      OnOffHelper onoff ("ns3::UdpSocketFactory",
                         InetSocketAddress (interfaces.GetAddress (chIf), APP_PORT));
      onoff.SetAttribute ("DataRate", StringValue (DATA_RATE));
      onoff.SetAttribute ("PacketSize", UintegerValue (PKT_SIZE));
      onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
      onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));

      ApplicationContainer app = onoff.Install (regularNodes.Get (n));
      app.Start (Seconds (startRng->GetValue ()));
      app.Stop (Seconds (TRAFFIC_STOP));
    }

  // PacketSink on each CH
  PacketSinkHelper sink ("ns3::UdpSocketFactory",
                         InetSocketAddress (Ipv4Address::GetAny (), APP_PORT));
  for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
    {
      sink.Install (chNodes.Get (c)).Start (Seconds (0.0));
    }

  std::cout << "  Traffic: " << NUM_REGULAR_NODES
            << " nodes -> " << NUM_CLUSTER_HEADS
            << " CHs (UDP " << DATA_RATE << ", " << PKT_SIZE << "B)\n\n";
}

// ============================================================
//  STEP 7: Results
// ============================================================
void
PrintResults (Ptr<FlowMonitor> flowMonitor, FlowMonitorHelper &flowHelper)
{
  flowMonitor->CheckForLostPackets ();

  Ptr<Ipv4FlowClassifier> cls =
    DynamicCast<Ipv4FlowClassifier> (flowHelper.GetClassifier ());
  FlowMonitor::FlowStatsContainer stats = flowMonitor->GetFlowStats ();

  uint64_t totTx = 0, totRx = 0, totRxB = 0;
  double totDelay = 0.0;
  uint32_t flows = 0, deadFlows = 0;

  std::ofstream csv ("cluster-aodv-nosink-results.csv");
  csv << "FlowID,SrcAddr,DstAddr,TxPackets,RxPackets,LostPackets,"
      << "PDR_pct,Throughput_kbps,AvgDelay_ms,AvgJitter_ms\n";

  for (auto &kv : stats)
    {
      auto ft = cls->FindFlow (kv.first);
      auto &s = kv.second;

      double pdr = s.txPackets > 0 ? (double)s.rxPackets / s.txPackets * 100.0 : 0.0;
      double dur = s.rxPackets > 0
        ? (s.timeLastRxPacket - s.timeFirstTxPacket).GetSeconds () : 0.0;
      double tput = dur > 0 ? s.rxBytes * 8.0 / dur / 1000.0 : 0.0;
      double delay = s.rxPackets > 0
        ? s.delaySum.GetMilliSeconds () / (double)s.rxPackets : 0.0;
      double jitter = s.rxPackets > 1
        ? s.jitterSum.GetMilliSeconds () / (double)(s.rxPackets - 1) : 0.0;

      totTx += s.txPackets; totRx += s.rxPackets;
      totRxB += s.rxBytes;
      totDelay += s.rxPackets > 0 ? s.delaySum.GetMilliSeconds () : 0.0;
      flows++;
      if (s.rxPackets == 0) deadFlows++;

      csv << kv.first << "," << ft.sourceAddress << "," << ft.destinationAddress
          << "," << s.txPackets << "," << s.rxPackets << "," << s.lostPackets
          << "," << std::fixed << std::setprecision (2)
          << pdr << "," << tput << "," << delay << "," << jitter << "\n";
    }
  csv.close ();

  double pdr = totTx > 0 ? (double)totRx / totTx * 100.0 : 0.0;
  double avgD = totRx > 0 ? totDelay / totRx : 0.0;
  double tput = SIM_TIME > 0 ? totRxB * 8.0 / SIM_TIME / 1000.0 : 0.0;

  std::cout << "\n============================================================\n"
    << "  RESULTS (No Sink)\n"
    << "============================================================\n"
    << "  Flows: " << flows << " (dead: " << deadFlows << ")\n"
    << "  Tx: " << totTx << " pkts | Rx: " << totRx << " pkts\n"
    << "  PDR: " << std::fixed << std::setprecision (2) << pdr << "%\n"
    << "  Avg Delay: " << avgD << " ms\n"
    << "  Throughput: " << tput << " kbps\n"
    << "  Output: cluster-aodv-nosink-results.csv\n"
    << "============================================================\n\n";

  flowMonitor->SerializeToXmlFile ("cluster-aodv-nosink-flowmon.xml", true, true);
}

// ============================================================
//  MAIN
// ============================================================
int
main (int argc, char *argv[])
{
  uint32_t numRegular = NUM_REGULAR_NODES;
  uint32_t numCH      = NUM_CLUSTER_HEADS;
  double   simTime    = SIM_TIME;
  bool     enablePcap = false;
  bool     enableAnim = true;
  bool     verbose    = false;

  CommandLine cmd (__FILE__);
  cmd.AddValue ("numRegular", "Number of regular nodes", numRegular);
  cmd.AddValue ("numCH", "Number of cluster heads", numCH);
  cmd.AddValue ("simTime", "Simulation time (seconds)", simTime);
  cmd.AddValue ("pcap", "Enable PCAP tracing", enablePcap);
  cmd.AddValue ("anim", "Enable NetAnim output", enableAnim);
  cmd.AddValue ("verbose", "Enable verbose logging", verbose);
  cmd.Parse (argc, argv);

  if (verbose)
    LogComponentEnable ("ClusterAodvNoSink", LOG_LEVEL_INFO);

  SeedManager::SetSeed (42);
  SeedManager::SetRun (1);

  std::cout << "\n============================================================\n"
    << "  CLUSTER-BASED AODV (No Sink)\n"
    << "  Nodes: " << numRegular << " + " << numCH << " CH = "
    << (numRegular + numCH) << "\n"
    << "  Area: " << AREA_WIDTH << "x" << AREA_HEIGHT
    << "m | AODV | " << simTime << "s\n"
    << "============================================================\n";

  // Step 1: Create 200 Nodes
  NodeContainer regularNodes, chNodes, allNodes;
  CreateNodes (regularNodes, chNodes, allNodes);

  // Step 2: WiFi
  YansWifiPhyHelper wifiPhy;
  NetDeviceContainer devices = ConfigureWifi (allNodes, wifiPhy, enablePcap);

  // Step 3: AODV + IP
  Ipv4InterfaceContainer interfaces = InstallInternetStack (allNodes, devices);

  // Step 4: Position
  PositionNodes (regularNodes, chNodes);

  // Step 5: Node Join (Cluster Assignment)
  AssignNodesToClusters (regularNodes, chNodes);

  // Step 6: Traffic (Node -> CH)
  InstallTraffic (regularNodes, chNodes, interfaces);

  // Step 7: Monitoring
  FlowMonitorHelper flowHelper;
  Ptr<FlowMonitor> flowMonitor = flowHelper.InstallAll ();

  // NetAnim
  AnimationInterface *anim = nullptr;
  if (enableAnim)
    {
      anim = new AnimationInterface ("cluster-aodv-nosink-animation.xml");
      anim->SetMaxPktsPerTraceFile (500000);

      for (uint32_t i = 0; i < NUM_REGULAR_NODES; i++)
        {
          // Color nodes by cluster (cycle through colors)
          uint32_t ch = clusterAssignment[i];
          uint8_t r = (ch * 67) % 200 + 55;
          uint8_t g = (ch * 131) % 200 + 55;
          uint8_t b = (ch * 197) % 200 + 55;

          anim->UpdateNodeDescription (regularNodes.Get (i),
            "N" + std::to_string (i) + "->CH" + std::to_string (ch));
          anim->UpdateNodeColor (regularNodes.Get (i), r, g, b);
          anim->UpdateNodeSize (regularNodes.Get (i)->GetId (), 10, 10);
        }
      for (uint32_t i = 0; i < NUM_CLUSTER_HEADS; i++)
        {
          anim->UpdateNodeDescription (chNodes.Get (i),
            "CH" + std::to_string (i) + "[" + std::to_string (clusterSizes[i]) + "]");
          anim->UpdateNodeColor (chNodes.Get (i), 220, 20, 60);   // Crimson
          anim->UpdateNodeSize (chNodes.Get (i)->GetId (), 30, 30);
        }
    }

  // Run
  std::cout << "[RUN] Simulating " << simTime << "s...\n";
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  PrintResults (flowMonitor, flowHelper);

  Simulator::Destroy ();
  if (anim) delete anim;

  std::cout << "[DONE] Complete.\n\n";
  return 0;
}
