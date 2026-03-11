/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef MQTT_SN_BROKER_H
#define MQTT_SN_BROKER_H

#include "ns3/application.h"
#include "ns3/socket.h"
#include <map>

namespace ns3 {

struct BrokerStats
{
  uint32_t rxPackets = 0;
  uint32_t rxBytes = 0;
  uint32_t emergencies = 0;
  uint32_t fromGateways = 0;
  std::map<uint16_t, uint32_t> topicCounts;
  std::map<uint8_t, uint32_t> priorityCounts;
};

class MqttSnBroker : public Application
{
public:
  static TypeId GetTypeId (void);
  MqttSnBroker ();
  virtual ~MqttSnBroker ();

  void Setup (uint16_t port);
  BrokerStats GetStats () const;
  void PrintStats () const;

private:
  virtual void StartApplication (void);
  virtual void StopApplication (void);
  void HandleRead (Ptr<Socket> socket);

  Ptr<Socket>  m_socket;
  uint16_t     m_port;
  BrokerStats  m_stats;
};

} // namespace ns3
#endif
