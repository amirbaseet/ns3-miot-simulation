/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef MQTT_SN_GATEWAY_H
#define MQTT_SN_GATEWAY_H

#include "ns3/application.h"
#include "ns3/socket.h"
#include "ns3/address.h"
#include <map>
#include <queue>

namespace ns3 {

struct PriorityPacket
{
  uint8_t priority;
  uint16_t topicId;
  uint16_t msgId;
  uint32_t size;
  double rxTime;
  uint8_t qos;
  bool emergency;

  bool operator< (const PriorityPacket &other) const
  {
    if (priority != other.priority) return priority < other.priority;
    return rxTime > other.rxTime;
  }
};

struct GatewayStats
{
  uint32_t rxPackets = 0;
  uint32_t rxBytes = 0;
  uint32_t connects = 0;
  uint32_t disconnects = 0;
  uint32_t emergencies = 0;
  uint32_t forwardedToBroker = 0;
  std::map<uint16_t, uint32_t> topicCounts;
  std::map<uint8_t, uint32_t> priorityCounts;
  uint32_t processedHigh = 0;
  uint32_t processedMed = 0;
  uint32_t processedLow = 0;
};

class MqttSnGateway : public Application
{
public:
  static TypeId GetTypeId (void);
  MqttSnGateway ();
  virtual ~MqttSnGateway ();

  void Setup (uint16_t port);
  void SetBroker (Ipv4Address brokerAddr, uint16_t brokerPort);
  GatewayStats GetStats () const;
  void PrintStats () const;

private:
  virtual void StartApplication (void);
  virtual void StopApplication (void);

  void HandleRead (Ptr<Socket> socket);
  void ProcessQueue (void);
  void ForwardToBroker (PriorityPacket &pp);
  void SendConnAck (Ptr<Socket> socket, Address from);
  void SendPubAck (Ptr<Socket> socket, Address from, uint16_t msgId);

  Ptr<Socket>  m_socket;
  Ptr<Socket>  m_brokerSocket;
  uint16_t     m_port;
  Ipv4Address  m_brokerAddr;
  uint16_t     m_brokerPort;
  bool         m_hasBroker;
  GatewayStats m_stats;
  std::priority_queue<PriorityPacket> m_pQueue;
};

} // namespace ns3
#endif
