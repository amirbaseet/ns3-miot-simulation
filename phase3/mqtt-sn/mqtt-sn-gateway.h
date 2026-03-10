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
  uint8_t priority;   // 0=low, 1=medium, 2=high, 3=critical
  uint16_t topicId;
  uint16_t msgId;
  uint32_t size;
  double   rxTime;

  // Higher priority first, then earlier arrival
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
  std::map<uint16_t, uint32_t> topicCounts;
  std::map<uint8_t, uint32_t>  priorityCounts;  // priority -> count
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
  GatewayStats GetStats () const;
  void PrintStats () const;

private:
  virtual void StartApplication (void);
  virtual void StopApplication (void);

  void HandleRead (Ptr<Socket> socket);
  void ProcessQueue (void);
  void SendConnAck (Ptr<Socket> socket, Address from);
  void SendPubAck (Ptr<Socket> socket, Address from, uint16_t msgId);

  Ptr<Socket>  m_socket;
  uint16_t     m_port;
  GatewayStats m_stats;

  // Priority queue: high priority packets processed first
  std::priority_queue<PriorityPacket> m_pQueue;
};

} // namespace ns3
#endif
