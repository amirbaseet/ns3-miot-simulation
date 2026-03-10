/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Cluster-Based AODV Network Traffic Simulation
 * 
 * Author:  Amro Baseet
 * Date:    March 2026
 * 
 * Description:
 *   Simulates a 200-node wireless ad-hoc network organized into 20 clusters.
 *   Each cluster has a Cluster Head (CH) that aggregates sensor data and
 *   forwards it to a central sink node. Uses AODV routing protocol.
 *
 * Topology:
 *   - 180 regular nodes (IDs 0-179): random positions, send data to nearest CH
 *   - 20 Cluster Heads (IDs 180-199): grid positions, aggregate & forward to sink
 *   - 1 Sink node (ID 200): center position, collects all data
 *
 * Usage:
 *   ./ns3 run "cluster-aodv-sim --seed=1"
 *   ./ns3 run "cluster-aodv-sim --seed=1 --verbose=true"
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

#include "aggregator-app.h"

#include <vector>
#include <cmath>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <iomanip>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("ClusterAodvSim");

// ============================================================================
//  SIMULATION PARAMETERS
// ============================================================================
static const uint32_t NUM_REGULAR_NODES = 180;
static const uint32_t NUM_CLUSTER_HEADS = 20;
static const uint32_t NUM_SINK          = 1;
static const uint32_t TOTAL_NODES       = NUM_REGULAR_NODES + NUM_CLUSTER_HEADS + NUM_SINK;

static const double   AREA_WIDTH        = 2000.0;  // meters
static const double   AREA_HEIGHT       = 2000.0;  // meters

static const uint32_t CH_GRID_COLS      = 5;       // 5 columns
static const uint32_t CH_GRID_ROWS      = 4;       // 4 rows (5x4 = 20 CHs)

static const double   SIM_TIME          = 100.0;   // seconds

// Tier-1: Regular Node -> CH
static const uint16_t TIER1_PORT        = 9090;
static const std::string TIER1_DATA_RATE = "8kbps";
static const uint32_t TIER1_PKT_SIZE    = 512;     // bytes
static const double   TIER1_START_MIN   = 1.0;     // sec
static const double   TIER1_START_MAX   = 5.0;     // sec
static const double   TIER1_STOP        = 95.0;    // sec

// Tier-2: CH -> Sink (via AggregatorApp)
static const uint16_t TIER2_PORT        = 9091;
static const uint32_t AGG_THRESHOLD     = 5;       // packets
static const double   AGG_TIMEOUT       = 2.0;     // seconds

// ============================================================================
//  HELPER: Compute Euclidean distance
// ============================================================================
double
ComputeDistance (double x1, double y1, double x2, double y2)
{
  return std::sqrt ((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}

// ============================================================================
//  HELPER: Get node position
// ============================================================================
Vector
GetNodePosition (Ptr<Node> node)
{
  Ptr<MobilityModel> mob = node->GetObject<MobilityModel> ();
  return mob->GetPosition ();
}

// ============================================================================
//  MAIN
// ============================================================================
int
main (int argc, char *argv[])
{
  // --- Command line arguments ---
  uint32_t seed = 1;
  bool verbose = false;
  bool enableNetAnim = false;
  bool enablePcap = true;

  CommandLine cmd;
  cmd.AddValue ("seed", "Random seed run number (1-5)", seed);
  cmd.AddValue ("verbose", "Enable verbose logging", verbose);
  cmd.AddValue ("netanim", "Enable NetAnim XML output", enableNetAnim);
  cmd.AddValue ("pcap", "Enable PCAP tracing on CH+Sink", enablePcap);
  cmd.Parse (argc, argv);

  // --- Logging ---
  if (verbose)
    {
      LogComponentEnable ("ClusterAodvSim", LOG_LEVEL_INFO);
      LogComponentEnable ("AggregatorApp", LOG_LEVEL_INFO);
    }

  // --- Random seed management ---
  RngSeedManager::SetSeed (1);
  RngSeedManager::SetRun (seed);

  NS_LOG_INFO ("==============================================");
  NS_LOG_INFO ("  Cluster-Based AODV Simulation");
  NS_LOG_INFO ("  Seed: " << seed);
  NS_LOG_INFO ("  Nodes: " << TOTAL_NODES << " (180 regular + 20 CH + 1 sink)");
  NS_LOG_INFO ("  Area: " << AREA_WIDTH << "m x " << AREA_HEIGHT << "m");
  NS_LOG_INFO ("  Sim Time: " << SIM_TIME << "s");
  NS_LOG_INFO ("==============================================");

  // ====================================================================
  //  STEP 1: Create Nodes
  // ====================================================================
  NodeContainer regularNodes;
  regularNodes.Create (NUM_REGULAR_NODES);  // IDs 0-179

  NodeContainer chNodes;
  chNodes.Create (NUM_CLUSTER_HEADS);       // IDs 180-199

  NodeContainer sinkNode;
  sinkNode.Create (NUM_SINK);              // ID 200

  NodeContainer allNodes;
  allNodes.Add (regularNodes);
  allNodes.Add (chNodes);
  allNodes.Add (sinkNode);

  NS_LOG_INFO ("Created " << allNodes.GetN () << " nodes");

  // ====================================================================
  //  STEP 2: Configure Wi-Fi (802.11b Ad-Hoc)
  // ====================================================================
  WifiHelper wifi;
  wifi.SetStandard (WIFI_STANDARD_80211b);
  wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue ("DsssRate11Mbps"),
                                 "ControlMode", StringValue ("DsssRate1Mbps"));

  YansWifiPhyHelper wifiPhy;
  YansWifiChannelHelper wifiChannel;
  wifiChannel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  wifiChannel.AddPropagationLoss ("ns3::LogDistancePropagationLossModel",
                                   "Exponent", DoubleValue (3.0),
                                   "ReferenceLoss", DoubleValue (46.6777));
  wifiPhy.SetChannel (wifiChannel.Create ());

  WifiMacHelper wifiMac;
  wifiMac.SetType ("ns3::AdhocWifiMac");

  NetDeviceContainer allDevices = wifi.Install (wifiPhy, wifiMac, allNodes);

  NS_LOG_INFO ("Wi-Fi 802.11b Ad-Hoc configured with LogDistance propagation");

  // ====================================================================
  //  STEP 3: Install Internet Stack + AODV
  // ====================================================================
  AodvHelper aodv;
  InternetStackHelper internet;
  internet.SetRoutingHelper (aodv);
  internet.Install (allNodes);

  // ====================================================================
  //  STEP 4: Assign IP Addresses
  // ====================================================================
  Ipv4AddressHelper ipv4;
  ipv4.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer allInterfaces = ipv4.Assign (allDevices);

  NS_LOG_INFO ("IPv4 addresses assigned: 10.1.1.0/24");

  // ====================================================================
  //  STEP 5: Set Node Positions
  // ====================================================================

  // --- 5a: Position Cluster Heads in 4x5 grid ---
  MobilityHelper chMobility;
  Ptr<ListPositionAllocator> chPositions = CreateObject<ListPositionAllocator> ();

  double xSpacing = AREA_WIDTH / CH_GRID_COLS;    // 400m
  double ySpacing = AREA_HEIGHT / CH_GRID_ROWS;   // 500m

  for (uint32_t i = 0; i < NUM_CLUSTER_HEADS; i++)
    {
      uint32_t col = i % CH_GRID_COLS;
      uint32_t row = i / CH_GRID_COLS;
      double x = (col + 0.5) * xSpacing;
      double y = (row + 0.5) * ySpacing;
      chPositions->Add (Vector (x, y, 0.0));
      NS_LOG_INFO ("CH " << (NUM_REGULAR_NODES + i) << " position: ("
                   << x << ", " << y << ")");
    }

  chMobility.SetPositionAllocator (chPositions);
  chMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  chMobility.Install (chNodes);

  // --- 5b: Position regular nodes randomly ---
  MobilityHelper regularMobility;
  std::ostringstream xRange, yRange;
  xRange << "ns3::UniformRandomVariable[Min=0.0|Max=" << AREA_WIDTH << "]";
  yRange << "ns3::UniformRandomVariable[Min=0.0|Max=" << AREA_HEIGHT << "]";

  regularMobility.SetPositionAllocator (
    "ns3::RandomRectanglePositionAllocator",
    "X", StringValue (xRange.str ()),
    "Y", StringValue (yRange.str ()));
  regularMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  regularMobility.Install (regularNodes);

  // --- 5c: Position sink at center ---
  MobilityHelper sinkMobility;
  Ptr<ListPositionAllocator> sinkPos = CreateObject<ListPositionAllocator> ();
  sinkPos->Add (Vector (AREA_WIDTH / 2.0, AREA_HEIGHT / 2.0, 0.0));
  sinkMobility.SetPositionAllocator (sinkPos);
  sinkMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  sinkMobility.Install (sinkNode);

  NS_LOG_INFO ("Sink node position: (" << AREA_WIDTH / 2.0 << ", "
               << AREA_HEIGHT / 2.0 << ")");

  // ====================================================================
  //  STEP 6: Cluster Assignment (nearest CH)
  // ====================================================================
  std::vector<uint32_t> clusterMap (NUM_REGULAR_NODES);  // node_id -> ch_index

  for (uint32_t n = 0; n < NUM_REGULAR_NODES; n++)
    {
      Vector nPos = GetNodePosition (regularNodes.Get (n));
      double bestDist = 1e9;
      uint32_t bestCH = 0;

      for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
        {
          Vector cPos = GetNodePosition (chNodes.Get (c));
          double dist = ComputeDistance (nPos.x, nPos.y, cPos.x, cPos.y);
          if (dist < bestDist)
            {
              bestDist = dist;
              bestCH = c;
            }
        }

      clusterMap[n] = bestCH;
      NS_LOG_DEBUG ("Node " << n << " -> CH " << (NUM_REGULAR_NODES + bestCH)
                    << " (dist=" << std::fixed << std::setprecision(1)
                    << bestDist << "m)");
    }

  // Log cluster sizes
  std::vector<uint32_t> clusterSizes (NUM_CLUSTER_HEADS, 0);
  for (uint32_t n = 0; n < NUM_REGULAR_NODES; n++)
    {
      clusterSizes[clusterMap[n]]++;
    }
  for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
    {
      NS_LOG_INFO ("Cluster " << c << " (CH " << (NUM_REGULAR_NODES + c)
                   << "): " << clusterSizes[c] << " members");
    }

  // ====================================================================
  //  STEP 7: Install Tier-1 Traffic (Regular Node -> CH)
  // ====================================================================
  Ptr<UniformRandomVariable> startRng = CreateObject<UniformRandomVariable> ();
  startRng->SetAttribute ("Min", DoubleValue (TIER1_START_MIN));
  startRng->SetAttribute ("Max", DoubleValue (TIER1_START_MAX));

  for (uint32_t n = 0; n < NUM_REGULAR_NODES; n++)
    {
      uint32_t chIdx = clusterMap[n];

      // Get CH IP address
      // CH nodes start at index NUM_REGULAR_NODES in allInterfaces
      Ipv4Address chIp = allInterfaces.GetAddress (NUM_REGULAR_NODES + chIdx);

      // Create OnOff application on regular node
      OnOffHelper onoff ("ns3::UdpSocketFactory",
                          InetSocketAddress (chIp, TIER1_PORT));
      onoff.SetAttribute ("DataRate", StringValue (TIER1_DATA_RATE));
      onoff.SetAttribute ("PacketSize", UintegerValue (TIER1_PKT_SIZE));
      onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1.0]"));
      onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0.0]"));

      ApplicationContainer app = onoff.Install (regularNodes.Get (n));
      double startTime = startRng->GetValue ();
      app.Start (Seconds (startTime));
      app.Stop (Seconds (TIER1_STOP));

      NS_LOG_DEBUG ("Tier-1: Node " << n << " -> CH " << (NUM_REGULAR_NODES + chIdx)
                    << " (" << chIp << ":" << TIER1_PORT << ")"
                    << " start=" << std::fixed << std::setprecision(2) << startTime << "s");
    }

  NS_LOG_INFO ("Tier-1 traffic installed: " << NUM_REGULAR_NODES
               << " OnOff applications -> " << NUM_CLUSTER_HEADS << " CHs");

  // ====================================================================
  //  STEP 8: Install Tier-2 (AggregatorApp on each CH)
  // ====================================================================
  // Get sink IP address (last node in allInterfaces)
  Ipv4Address sinkIp = allInterfaces.GetAddress (TOTAL_NODES - 1);

  for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
    {
      Ptr<AggregatorApp> aggApp = CreateObject<AggregatorApp> ();
      aggApp->SetSinkAddress (sinkIp, TIER2_PORT);
      aggApp->SetAggregationParams (AGG_THRESHOLD, AGG_TIMEOUT);

      chNodes.Get (c)->AddApplication (aggApp);
      aggApp->SetStartTime (Seconds (1.0));
      aggApp->SetStopTime (Seconds (99.0));

      NS_LOG_DEBUG ("Tier-2: AggregatorApp on CH " << (NUM_REGULAR_NODES + c)
                    << " -> Sink " << sinkIp << ":" << TIER2_PORT);
    }

  NS_LOG_INFO ("Tier-2 installed: " << NUM_CLUSTER_HEADS
               << " AggregatorApps -> Sink (" << sinkIp << ")");

  // ====================================================================
  //  STEP 9: Install PacketSink on Sink Node
  // ====================================================================
  PacketSinkHelper sinkHelper ("ns3::UdpSocketFactory",
                                InetSocketAddress (Ipv4Address::GetAny (), TIER2_PORT));
  ApplicationContainer sinkApps = sinkHelper.Install (sinkNode.Get (0));
  sinkApps.Start (Seconds (0.0));
  sinkApps.Stop (Seconds (SIM_TIME));

  NS_LOG_INFO ("PacketSink installed on sink node (port " << TIER2_PORT << ")");

  // ====================================================================
  //  STEP 10: Install FlowMonitor
  // ====================================================================
  FlowMonitorHelper flowHelper;
  Ptr<FlowMonitor> flowMonitor = flowHelper.InstallAll ();

  // ====================================================================
  //  STEP 11: Enable PCAP (CH + Sink only)
  // ====================================================================
  if (enablePcap)
    {
      std::ostringstream pcapPrefix;
      pcapPrefix << "results/cluster-aodv-seed" << seed;

      // PCAP for CH nodes
      for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
        {
          uint32_t globalIdx = NUM_REGULAR_NODES + c;
          wifiPhy.EnablePcap (pcapPrefix.str () + "-ch",
                              allDevices.Get (globalIdx), false);
        }

      // PCAP for sink
      wifiPhy.EnablePcap (pcapPrefix.str () + "-sink",
                          allDevices.Get (TOTAL_NODES - 1), false);

      NS_LOG_INFO ("PCAP enabled for CH nodes and sink");
    }

  // ====================================================================
  //  STEP 12: NetAnim (optional)
  // ====================================================================
  AnimationInterface *anim = nullptr;
  if (enableNetAnim)
    {
      std::ostringstream animFile;
      animFile << "results/cluster-aodv-anim-seed" << seed << ".xml";
      anim = new AnimationInterface (animFile.str ());

      // Color code nodes
      for (uint32_t n = 0; n < NUM_REGULAR_NODES; n++)
        {
          anim->UpdateNodeColor (regularNodes.Get (n), 0, 150, 255);  // Blue
          anim->UpdateNodeSize (n, 5, 5);
        }
      for (uint32_t c = 0; c < NUM_CLUSTER_HEADS; c++)
        {
          anim->UpdateNodeColor (chNodes.Get (c), 255, 100, 0);  // Orange
          anim->UpdateNodeSize (NUM_REGULAR_NODES + c, 10, 10);
        }
      anim->UpdateNodeColor (sinkNode.Get (0), 255, 0, 0);  // Red
      anim->UpdateNodeSize (TOTAL_NODES - 1, 15, 15);

      NS_LOG_INFO ("NetAnim enabled: " << animFile.str ());
    }

  // ====================================================================
  //  STEP 13: Run Simulation
  // ====================================================================
  NS_LOG_INFO ("Starting simulation...");
  Simulator::Stop (Seconds (SIM_TIME));
  Simulator::Run ();

  // ====================================================================
  //  STEP 14: Collect and Export Results
  // ====================================================================

  // --- FlowMonitor XML ---
  std::ostringstream flowFile;
  flowFile << "results/flowmon-seed" << seed << ".xml";
  flowMonitor->SerializeToXmlFile (flowFile.str (), true, true);
  NS_LOG_INFO ("FlowMonitor results: " << flowFile.str ());

  // --- Print summary statistics ---
  FlowMonitor::FlowStatsContainer stats = flowMonitor->GetFlowStats ();

  uint64_t totalTxPackets = 0, totalRxPackets = 0;
  uint64_t totalTxBytes = 0, totalRxBytes = 0;
  double totalDelay = 0.0;
  uint32_t flowCount = 0;

  for (auto it = stats.begin (); it != stats.end (); ++it)
    {
      totalTxPackets += it->second.txPackets;
      totalRxPackets += it->second.rxPackets;
      totalTxBytes   += it->second.txBytes;
      totalRxBytes   += it->second.rxBytes;

      if (it->second.rxPackets > 0)
        {
          totalDelay += it->second.delaySum.GetSeconds ();
          flowCount++;
        }
    }

  double pdr = (totalTxPackets > 0) ?
    (double)totalRxPackets / totalTxPackets * 100.0 : 0.0;
  double throughput = (SIM_TIME > 0) ?
    (double)totalRxBytes * 8.0 / SIM_TIME / 1000.0 : 0.0;  // kbps
  double avgDelay = (totalRxPackets > 0) ?
    totalDelay / totalRxPackets * 1000.0 : 0.0;  // ms

  std::cout << "\n============================================" << std::endl;
  std::cout << "  SIMULATION RESULTS (Seed " << seed << ")" << std::endl;
  std::cout << "============================================" << std::endl;
  std::cout << "  Total flows:        " << stats.size () << std::endl;
  std::cout << "  Tx Packets:         " << totalTxPackets << std::endl;
  std::cout << "  Rx Packets:         " << totalRxPackets << std::endl;
  std::cout << "  Packet Loss:        " << (totalTxPackets - totalRxPackets) << std::endl;
  std::cout << "  PDR:                " << std::fixed << std::setprecision(2)
            << pdr << "%" << std::endl;
  std::cout << "  Throughput:         " << std::fixed << std::setprecision(2)
            << throughput << " kbps" << std::endl;
  std::cout << "  Avg E2E Delay:      " << std::fixed << std::setprecision(2)
            << avgDelay << " ms" << std::endl;
  std::cout << "============================================\n" << std::endl;

  // --- Save summary to CSV ---
  std::ostringstream csvFile;
  csvFile << "results/metrics-seed" << seed << ".csv";
  std::ofstream csv (csvFile.str ());
  csv << "seed,total_flows,tx_packets,rx_packets,packet_loss,pdr_percent,"
      << "throughput_kbps,avg_delay_ms" << std::endl;
  csv << seed << ","
      << stats.size () << ","
      << totalTxPackets << ","
      << totalRxPackets << ","
      << (totalTxPackets - totalRxPackets) << ","
      << std::fixed << std::setprecision(4) << pdr << ","
      << std::fixed << std::setprecision(4) << throughput << ","
      << std::fixed << std::setprecision(4) << avgDelay << std::endl;
  csv.close ();
  NS_LOG_INFO ("Metrics saved: " << csvFile.str ());

  // --- Cleanup ---
  Simulator::Destroy ();
  if (anim)
    {
      delete anim;
    }

  return 0;
}
