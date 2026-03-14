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
static const double   SIM_TIME   = 300.0;
static const uint32_t PKT_SIZE   = 512;
static const std::string DATA_RATE = "4kbps";
static const uint16_t APP_PORT   = 9;
static const uint16_t SINK_PORT  = 10;
static const double   START_MIN  = 5.0;
static const double   START_MAX  = 20.0;
static const double   STOP_TIME  = 95.0;

// Dynamic (sized at runtime)
std::vector<uint32_t> clusterAssign;
std::vector<uint32_t> clusterSizes;

// ============================================================
// UdpForwarder: Receives packets and forwards them to sink
// This is REAL forwarding — CH only sends to sink what it receives
// ============================================================
class UdpForwarder : public Application
{
public:
  static TypeId GetTypeId (void)
  {
    static TypeId tid = TypeId ("ns3::UdpForwarder")
      .SetParent<Application> ()
      .AddConstructor<UdpForwarder> ();
    return tid;
  }

  UdpForwarder () : m_rxSocket (nullptr), m_txSocket (nullptr),
    m_rxPort (0), m_rxCount (0), m_fwdCount (0), m_fwdEnabled (false) {}

  virtual ~UdpForwarder () {}

  void Setup (uint16_t rxPort, Ipv4Address sinkAddr, uint16_t sinkPort)
  {
    m_rxPort = rxPort;
    m_sinkAddr = sinkAddr;
    m_sinkPort = sinkPort;
    m_fwdEnabled = true;
  }

  void SetupNoForward (uint16_t rxPort)
  {
    m_rxPort = rxPort;
    m_fwdEnabled = false;
  }

  uint32_t GetRxCount () const { return m_rxCount; }
  uint32_t GetFwdCount () const { return m_fwdCount; }

private:
  virtual void StartApplication (void)
  {
    // Receive socket
    m_rxSocket = Socket::CreateSocket (GetNode (), UdpSocketFactory::GetTypeId ());
    m_rxSocket->Bind (InetSocketAddress (Ipv4Address::GetAny (), m_rxPort));
    m_rxSocket->SetRecvCallback (MakeCallback (&UdpForwarder::HandleRead, this));

    // Forward socket (if enabled)
    if (m_fwdEnabled)
      {
        m_txSocket = Socket::CreateSocket (GetNode (), UdpSocketFactory::GetTypeId ());
        m_txSocket->Bind ();
      }
  }

  virtual void StopApplication (void)
  {
    if (m_rxSocket) { m_rxSocket->Close (); }
    if (m_txSocket) { m_txSocket->Close (); }
  }

  void HandleRead (Ptr<Socket> socket)
  {
    Ptr<Packet> packet;
    Address from;
    while ((packet = socket->RecvFrom (from)))
      {
        m_rxCount++;

        // Forward to sink (real forwarding — same packet)
        if (m_fwdEnabled && m_txSocket)
          {
            Ptr<Packet> fwdPkt = Create<Packet> (packet->GetSize ());
            m_txSocket->SendTo (fwdPkt, 0,
              InetSocketAddress (m_sinkAddr, m_sinkPort));
            m_fwdCount++;
          }
      }
  }

  Ptr<Socket>  m_rxSocket;
  Ptr<Socket>  m_txSocket;
  uint16_t     m_rxPort;
  Ipv4Address  m_sinkAddr;
  uint16_t     m_sinkPort;
  uint32_t     m_rxCount;
  uint32_t     m_fwdCount;
  bool         m_fwdEnabled;
};

NS_OBJECT_ENSURE_REGISTERED (UdpForwarder);

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

void PositionNodes (NodeContainer &sens, NodeContainer &chs, NodeContainer &sinkNode,
                    uint32_t nCH)
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

  // Sink at center
  Ptr<ListPositionAllocator> skp = CreateObject<ListPositionAllocator> ();
  skp->Add (Vector (AREA/2.0, AREA/2.0, 0));
  m.SetPositionAllocator (skp); m.Install (sinkNode);
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
                     NodeContainer &sinkNode, Ipv4InterfaceContainer &ifaces,
                     uint32_t nSens, bool useSink, bool hetero)
{
  Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable> ();
  rng->SetAttribute ("Min", DoubleValue (START_MIN));
  rng->SetAttribute ("Max", DoubleValue (START_MAX));

  uint32_t nCH = chs.GetN ();
  uint32_t sinkIfIdx = nSens + nCH;
  uint32_t nECG = nSens / 3;
  uint32_t nHR  = nSens / 3;

  // Sensor -> CH traffic (OnOff UDP)
  for (uint32_t n = 0; n < nSens; n++)
    {
      uint32_t chIf = nSens + clusterAssign[n];

      std::string rate;
      uint32_t pktSize;

      if (hetero)
        {
          // Match MQTT-SN traffic profile: ECG=4kbps/128B, HR=0.5kbps/64B, Temp=0.05kbps/32B
          if (n < nECG) { rate = "4kbps"; pktSize = 128; }
          else if (n < nECG + nHR) { rate = "512bps"; pktSize = 64; }
          else { rate = "51bps"; pktSize = 32; }
        }
      else
        {
          // Original constant rate
          rate = DATA_RATE;
          pktSize = PKT_SIZE;
        }

      OnOffHelper onoff ("ns3::UdpSocketFactory",
        InetSocketAddress (ifaces.GetAddress (chIf), APP_PORT));
      onoff.SetAttribute ("DataRate", StringValue (rate));
      onoff.SetAttribute ("PacketSize", UintegerValue (pktSize));
      onoff.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
      onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
      ApplicationContainer app = onoff.Install (sens.Get (n));
      app.Start (Seconds (rng->GetValue ()));
      app.Stop (Seconds (STOP_TIME));
    }

  // CH: UdpForwarder
  for (uint32_t c = 0; c < nCH; c++)
    {
      Ptr<UdpForwarder> fwd = CreateObject<UdpForwarder> ();
      if (useSink)
        fwd->Setup (APP_PORT, ifaces.GetAddress (sinkIfIdx), SINK_PORT);
      else
        fwd->SetupNoForward (APP_PORT);
      chs.Get (c)->AddApplication (fwd);
      fwd->SetStartTime (Seconds (0.0));
      fwd->SetStopTime (Seconds (SIM_TIME));
    }

  // Sink
  if (useSink)
    {
      PacketSinkHelper sinkHelper ("ns3::UdpSocketFactory",
        InetSocketAddress (Ipv4Address::GetAny (), SINK_PORT));
      sinkHelper.Install (sinkNode.Get (0)).Start (Seconds (0.0));
    }

  if (hetero)
    std::cout << "  Traffic: HETEROGENEOUS (" << nECG << " ECG@4kbps + "
              << nHR << " HR@512bps + " << (nSens-nECG-nHR) << " Temp@51bps)\n";
  else
    std::cout << "  Traffic: CONSTANT (" << nSens << " x " << DATA_RATE << ", " << PKT_SIZE << "B)\n";

  if (useSink)
    std::cout << "  Flow: Sensors -> " << nCH << " CHs (forward) -> 1 Sink\n\n";
  else
    std::cout << "  Flow: Sensors -> " << nCH << " CHs (receive only)\n\n";
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
  uint32_t runNum     = 1;
  double   simTime    = 300.0;
  bool     useSink    = false;
  bool     hetero     = false;  // Heterogeneous traffic (match MQTT-SN load)
  bool     enableAnim = false;
  bool     verbose    = false;
  std::string csvName = "";

  CommandLine cmd (__FILE__);
  cmd.AddValue ("numRegular", "Number of regular sensor nodes", numRegular);
  cmd.AddValue ("numCH", "Number of cluster heads", numCH);
  cmd.AddValue ("run", "Run number for seed variation", runNum);
  cmd.AddValue ("simTime", "Simulation time (seconds)", simTime);
  cmd.AddValue ("useSink", "Enable sink/broker node", useSink);
  cmd.AddValue ("hetero", "Heterogeneous traffic (match MQTT-SN rates)", hetero);
  cmd.AddValue ("anim", "Enable NetAnim output", enableAnim);
  cmd.AddValue ("verbose", "Enable verbose logging", verbose);
  cmd.AddValue ("csv", "Output CSV filename", csvName);
  cmd.Parse (argc, argv);

  if (verbose)
    LogComponentEnable ("ClusterAodvNoSink", LOG_LEVEL_INFO);

  if (csvName.empty ())
    {
      std::ostringstream oss;
      oss << "wsn-" << numRegular << "nodes";
      if (useSink) oss << "-sink";
      oss << "-results.csv";
      csvName = oss.str ();
    }

  SeedManager::SetSeed (42);
  SeedManager::SetRun (runNum);

  uint32_t totalNodes = numRegular + numCH + 1; // +1 sink always created

  std::cout << "\n============================================================\n"
    << "  Traditional WSN (AODV + UDP)\n"
    << "  Sensors: " << numRegular << " | CHs: " << numCH
    << " | Sink: " << (useSink ? "yes" : "no")
    << " | Total: " << totalNodes << "\n"
    << "  Area: " << AREA << "x" << AREA << "m | AODV | " << simTime << "s\n"
    << "  CSV: " << csvName << "\n"
    << "============================================================\n\n";

  NodeContainer sens, chs, sinkNode, all;
  sens.Create (numRegular);
  chs.Create (numCH);
  sinkNode.Create (1);
  all.Add (sens); all.Add (chs); all.Add (sinkNode);

  YansWifiPhyHelper phy;
  NetDeviceContainer dev = ConfigWifi (all, phy);
  Ipv4InterfaceContainer ifaces = InstallStack (all, dev);

  PositionNodes (sens, chs, sinkNode, numCH);
  AssignClusters (sens, chs, numCH);
  InstallTraffic (sens, chs, sinkNode, ifaces, numRegular, useSink, hetero);

  FlowMonitorHelper fh;
  Ptr<FlowMonitor> fm = fh.InstallAll ();

  std::cout << "[RUN] " << simTime << "s...\n";
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  PrintResults (fm, fh, csvName);

  // Print CH forwarding stats
  if (useSink)
    {
      std::cout << "  Per-CH Forwarding Stats:\n";
      uint32_t totalRx = 0, totalFwd = 0;
      for (uint32_t c = 0; c < numCH; c++)
        {
          Ptr<UdpForwarder> fwd = DynamicCast<UdpForwarder> (chs.Get (c)->GetApplication (0));
          if (fwd)
            {
              std::cout << "    CH" << (numRegular + c) << " | Rx:" << fwd->GetRxCount ()
                        << " Fwd:" << fwd->GetFwdCount () << "\n";
              totalRx += fwd->GetRxCount ();
              totalFwd += fwd->GetFwdCount ();
            }
        }
      std::cout << "  Total: Rx=" << totalRx << " Fwd=" << totalFwd << "\n\n";
    }

  Simulator::Destroy ();
  std::cout << "[DONE]\n\n";
  return 0;
}
