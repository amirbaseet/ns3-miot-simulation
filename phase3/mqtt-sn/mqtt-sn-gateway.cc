/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "mqtt-sn-gateway.h"
#include "mqtt-sn-header.h"
#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/inet-socket-address.h"
#include "ns3/udp-socket-factory.h"
#include "ns3/packet.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("MqttSnGateway");
NS_OBJECT_ENSURE_REGISTERED (MqttSnGateway);

TypeId MqttSnGateway::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::MqttSnGateway")
    .SetParent<Application> ()
    .AddConstructor<MqttSnGateway> ();
  return tid;
}

MqttSnGateway::MqttSnGateway () : m_socket (nullptr), m_port (9) {}
MqttSnGateway::~MqttSnGateway () { m_socket = nullptr; }

void MqttSnGateway::Setup (uint16_t port) { m_port = port; }
GatewayStats MqttSnGateway::GetStats () const { return m_stats; }

void MqttSnGateway::PrintStats () const
{
  std::cout << "    CH" << GetNode ()->GetId ()
            << " | Rx:" << m_stats.rxPackets
            << " Emerg:" << m_stats.emergencies
            << " | Pri[H:" << m_stats.processedHigh
            << " M:" << m_stats.processedMed
            << " L:" << m_stats.processedLow << "]"
            << " | Topics:";
  for (auto &kv : m_stats.topicCounts)
    {
      MqttSnHeader tmp;
      tmp.SetTopicId (kv.first);
      std::cout << " " << tmp.GetTopicName () << "=" << kv.second;
    }
  std::cout << std::endl;
}

void MqttSnGateway::StartApplication (void)
{
  if (!m_socket)
    {
      m_socket = Socket::CreateSocket (GetNode (), UdpSocketFactory::GetTypeId ());
      m_socket->Bind (InetSocketAddress (Ipv4Address::GetAny (), m_port));
      m_socket->SetRecvCallback (MakeCallback (&MqttSnGateway::HandleRead, this));
    }
  NS_LOG_INFO ("[CH " << GetNode ()->GetId () << "] Gateway listening, port " << m_port);
}

void MqttSnGateway::StopApplication (void)
{
  // Process remaining queue
  ProcessQueue ();

  if (m_socket)
    {
      m_socket->Close ();
      m_socket->SetRecvCallback (MakeNullCallback<void, Ptr<Socket>> ());
    }
  PrintStats ();
}

void MqttSnGateway::HandleRead (Ptr<Socket> socket)
{
  Ptr<Packet> packet;
  Address from;

  while ((packet = socket->RecvFrom (from)))
    {
      MqttSnHeader header;
      packet->RemoveHeader (header);

      m_stats.rxPackets++;
      m_stats.rxBytes += packet->GetSize () + header.GetSerializedSize ();

      switch (header.GetMsgType ())
        {
        case MQTTSN_CONNECT:
          {
            m_stats.connects++;
            NS_LOG_INFO ("[CH " << GetNode ()->GetId ()
                         << "] CONNECT from " << InetSocketAddress::ConvertFrom (from).GetIpv4 ()
                         << " Topic=" << header.GetTopicName ()
                         << " Priority=" << header.GetPriorityName ());
            SendConnAck (socket, from);
            break;
          }

        case MQTTSN_PUBLISH:
          {
            m_stats.topicCounts[header.GetTopicId ()]++;
            m_stats.priorityCounts[header.GetPriority ()]++;

            // Check emergency
            if (header.IsEmergency ())
              {
                m_stats.emergencies++;
                NS_LOG_INFO ("[CH " << GetNode ()->GetId ()
                             << "] *** EMERGENCY *** from "
                             << InetSocketAddress::ConvertFrom (from).GetIpv4 ()
                             << " MsgID=" << header.GetMsgId ());
              }

            // Add to priority queue
            PriorityPacket pp;
            pp.priority = header.GetPriority ();
            pp.topicId  = header.GetTopicId ();
            pp.msgId    = header.GetMsgId ();
            pp.size     = header.GetPayloadSize ();
            pp.rxTime   = Simulator::Now ().GetSeconds ();
            m_pQueue.push (pp);

            NS_LOG_DEBUG ("[CH " << GetNode ()->GetId ()
                          << "] PUBLISH queued: Topic=" << header.GetTopicName ()
                          << " Priority=" << header.GetPriorityName ()
                          << " QueueSize=" << m_pQueue.size ());

            // Send PUBACK for QoS > 0
            if (header.GetQos () > 0)
              SendPubAck (socket, from, header.GetMsgId ());

            // Process queue (highest priority first)
            ProcessQueue ();
            break;
          }

        case MQTTSN_DISCONNECT:
          {
            m_stats.disconnects++;
            NS_LOG_INFO ("[CH " << GetNode ()->GetId ()
                         << "] DISCONNECT from "
                         << InetSocketAddress::ConvertFrom (from).GetIpv4 ());
            break;
          }

        default:
          NS_LOG_WARN ("[CH " << GetNode ()->GetId ()
                       << "] Unknown MsgType: " << (int)header.GetMsgType ());
          break;
        }
    }
}

void MqttSnGateway::ProcessQueue (void)
{
  // Process all queued packets in priority order
  while (!m_pQueue.empty ())
    {
      PriorityPacket pp = m_pQueue.top ();
      m_pQueue.pop ();

      // Track processed by priority level
      if (pp.priority >= 2)      m_stats.processedHigh++;
      else if (pp.priority == 1) m_stats.processedMed++;
      else                       m_stats.processedLow++;

      NS_LOG_DEBUG ("[CH " << GetNode ()->GetId ()
                    << "] PROCESSED: Priority=" << (int)pp.priority
                    << " Topic=" << pp.topicId
                    << " MsgID=" << pp.msgId
                    << " Remaining=" << m_pQueue.size ());
    }
}

void MqttSnGateway::SendConnAck (Ptr<Socket> socket, Address from)
{
  Ptr<Packet> pkt = Create<Packet> ();
  MqttSnHeader h;
  h.SetMsgType (MQTTSN_CONNACK);
  h.SetQos (0); h.SetEmergency (false);
  pkt->AddHeader (h);
  socket->SendTo (pkt, 0, from);
}

void MqttSnGateway::SendPubAck (Ptr<Socket> socket, Address from, uint16_t msgId)
{
  Ptr<Packet> pkt = Create<Packet> ();
  MqttSnHeader h;
  h.SetMsgType (MQTTSN_PUBACK);
  h.SetMsgId (msgId);
  h.SetQos (0); h.SetEmergency (false);
  pkt->AddHeader (h);
  socket->SendTo (pkt, 0, from);
}

} // namespace ns3
