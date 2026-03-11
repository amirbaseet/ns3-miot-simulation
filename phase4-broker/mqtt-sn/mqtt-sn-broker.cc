/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "mqtt-sn-broker.h"
#include "mqtt-sn-header.h"
#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/inet-socket-address.h"
#include "ns3/udp-socket-factory.h"
#include "ns3/packet.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("MqttSnBroker");
NS_OBJECT_ENSURE_REGISTERED (MqttSnBroker);

TypeId MqttSnBroker::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::MqttSnBroker")
    .SetParent<Application> ()
    .AddConstructor<MqttSnBroker> ();
  return tid;
}

MqttSnBroker::MqttSnBroker () : m_socket (nullptr), m_port (1884) {}
MqttSnBroker::~MqttSnBroker () { m_socket = nullptr; }

void MqttSnBroker::Setup (uint16_t port) { m_port = port; }
BrokerStats MqttSnBroker::GetStats () const { return m_stats; }

void MqttSnBroker::PrintStats () const
{
  std::cout << "\n  ============================================\n"
            << "  BROKER (SINK) STATISTICS\n"
            << "  ============================================\n"
            << "  Total Rx Packets  : " << m_stats.rxPackets << "\n"
            << "  Total Rx Bytes    : " << m_stats.rxBytes << "\n"
            << "  From Gateways     : " << m_stats.fromGateways << "\n"
            << "  Emergencies       : " << m_stats.emergencies << "\n"
            << "  ---\n"
            << "  Per-Topic Breakdown:\n";
  for (auto &kv : m_stats.topicCounts)
    {
      MqttSnHeader tmp;
      tmp.SetTopicId (kv.first);
      std::cout << "    " << tmp.GetTopicName () << " (ID=" << kv.first
                << "): " << kv.second << " packets\n";
    }
  std::cout << "  Per-Priority Breakdown:\n";
  for (auto &kv : m_stats.priorityCounts)
    {
      MqttSnHeader tmp;
      tmp.SetQos (kv.first);
      std::string name;
      switch (kv.first) {
        case 3: name = "CRITICAL"; break;
        case 2: name = "HIGH"; break;
        case 1: name = "MEDIUM"; break;
        default: name = "LOW"; break;
      }
      std::cout << "    " << name << " (" << (int)kv.first
                << "): " << kv.second << " packets\n";
    }
  std::cout << "  ============================================\n\n";
}

void MqttSnBroker::StartApplication (void)
{
  if (!m_socket)
    {
      m_socket = Socket::CreateSocket (GetNode (), UdpSocketFactory::GetTypeId ());
      m_socket->Bind (InetSocketAddress (Ipv4Address::GetAny (), m_port));
      m_socket->SetRecvCallback (MakeCallback (&MqttSnBroker::HandleRead, this));
    }
  NS_LOG_INFO ("[BROKER] Listening on port " << m_port);
}

void MqttSnBroker::StopApplication (void)
{
  if (m_socket)
    {
      m_socket->Close ();
      m_socket->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
    }
  PrintStats ();
}

void MqttSnBroker::HandleRead (Ptr<Socket> socket)
{
  Ptr<Packet> packet;
  Address from;

  while ((packet = socket->RecvFrom (from)))
    {
      MqttSnHeader header;
      packet->RemoveHeader (header);

      m_stats.rxPackets++;
      m_stats.rxBytes += packet->GetSize () + header.GetSerializedSize ();
      m_stats.fromGateways++;
      m_stats.topicCounts[header.GetTopicId ()]++;
      m_stats.priorityCounts[header.GetPriority ()]++;

      if (header.IsEmergency ())
        {
          m_stats.emergencies++;
          NS_LOG_INFO ("[BROKER] *** EMERGENCY *** from "
                       << InetSocketAddress::ConvertFrom (from).GetIpv4 ()
                       << " Topic=" << header.GetTopicName ()
                       << " MsgID=" << header.GetMsgId ());
        }
      else
        {
          NS_LOG_DEBUG ("[BROKER] Rx from "
                        << InetSocketAddress::ConvertFrom (from).GetIpv4 ()
                        << " Topic=" << header.GetTopicName ()
                        << " Priority=" << header.GetPriorityName ());
        }
    }
}

} // namespace ns3
