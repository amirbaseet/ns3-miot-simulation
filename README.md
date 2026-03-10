# ns3-miot-simulation

## Cluster-Based AODV with MQTT-SN for Medical IoT (MIoT)

A comprehensive ns-3 network simulation for Medical Internet of Things. Implements cluster-based wireless sensor network with AODV routing and priority-aware MQTT-SN messaging protocol.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    1000m × 1000m Area                    │
│                                                         │
│   [ECG]──┐    [HR]──┐     [Temp]──┐                    │
│   [ECG]──┼──→ [GW0] │      [HR]──┼──→ [GW1]           │
│   [ECG]──┘    [HR]──┘     [Temp]──┘                    │
│                                                         │
│   Priority: HIGH    MEDIUM       LOW                    │
│   QoS:      2       1            0                      │
│   Interval: 250ms   1s           5s                     │
│                                                         │
│   ★ Emergency alerts: CRITICAL priority (random 0.5%)   │
│                                                         │
│   Routing: AODV (Ad-hoc On-Demand Distance Vector)      │
│   Transport: UDP                                        │
│   Application: MQTT-SN (Publish/Subscribe)              │
│   Wireless: IEEE 802.11b Ad-Hoc                         │
└─────────────────────────────────────────────────────────┘
```

### Node Types

| Type | Count | Role | Color (NetAnim) |
|------|-------|------|-----------------|
| ECG Sensors | 60 | Publish ECG data every 250ms | 🔴 Red |
| Heart Rate Sensors | 60 | Publish HR data every 1s | 🔵 Blue |
| Temperature Sensors | 60 | Publish temp data every 5s | 🟢 Green |
| Cluster Head (Gateway) | 20 | Receive & process with priority queue | 🟣 Purple |

---

## 📊 Results

### Phase Comparison

| Metric | Phase 1 (OnOff) | Phase 2 (MQTT-SN) | Phase 3 (Priority) |
|--------|:---:|:---:|:---:|
| **PDR** | 79.81% | 98.21% | **99.97%** |
| **Avg Delay** | 99.81 ms | 13.01 ms | **0.85 ms** |
| **Dead Flows** | 123 | 62 | **15** |
| **Emergencies** | - | - | **126** |

### Key Findings

- MQTT-SN with heterogeneous sensor traffic reduces network load by 88% vs constant-rate OnOff
- Priority queue ensures ECG (critical) packets are processed before temperature (low priority)
- Emergency detection alerts are delivered with CRITICAL priority (QoS=3)
- Cluster-based architecture with 20 CHs effectively manages 180 sensor nodes

---

## 🚀 Quick Start

### Prerequisites

```bash
# ns-3-dev installed at ~/ns-3-dev
# Python 3
pip install matplotlib pandas --break-system-packages
```

### Run Phase 1 (Baseline AODV)

```bash
cp phase1/cluster-aodv-nosink.cc ~/ns-3-dev/scratch/
cd ~/ns-3-dev
./ns3 build
./ns3 run cluster-aodv-nosink
```

### Run Phase 3 (Priority MQTT-SN)

```bash
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-mqtt
cp phase3/mqtt-sn/* ~/ns-3-dev/scratch/cluster-aodv-mqtt/
cd ~/ns-3-dev
./ns3 build
./ns3 run cluster-aodv-mqtt
```

### Run with Options

```bash
# Verbose mode (see MQTT-SN messages)
./ns3 run "cluster-aodv-mqtt --verbose=true"

# Faster (disable NetAnim)
./ns3 run "cluster-aodv-mqtt --anim=false"

# Short test
./ns3 run "cluster-aodv-mqtt --simTime=30"
```

### Analyze Results

```bash
# Copy results to project
cp ~/ns-3-dev/cluster-aodv-nosink-results.csv results/
cp ~/ns-3-dev/mqtt-sn-priority-results.csv results/

# Generate comparison graphs (8 graphs)
python3 compare_phases.py

# Analyze single phase
python3 analyze_results.py results/mqtt-sn-priority-results.csv
```

### View NetAnim

```bash
cd ~/ns-3-dev/netanim/build
./netanim
# Open: mqtt-sn-priority-animation.xml
```

---

## 📁 Project Structure

```
ns3-miot-simulation/
│
├── README.md                  ← This file
├── HOW_TO_RUN.md              ← Detailed run instructions
├── analyze_results.py         ← Single phase analyzer (6 graphs)
├── compare_phases.py          ← Phase comparison analyzer (8 graphs)
│
├── phase1/                    ← Phase 1: Baseline AODV
│   ├── cluster-aodv-nosink.cc    200 nodes → 20 CH (no sink)
│   └── cluster-aodv-sim.cc       200 nodes → 20 CH → 1 sink
│
├── phase3/                    ← Phase 3: Priority MQTT-SN
│   └── mqtt-sn/
│       ├── mqtt-sn-header.h       Packet format definition
│       ├── mqtt-sn-header.cc      Serialization + priority levels
│       ├── mqtt-sn-publisher.h    Sensor application
│       ├── mqtt-sn-publisher.cc   CONNECT/PUBLISH/DISCONNECT + emergency
│       ├── mqtt-sn-gateway.h      Gateway application
│       ├── mqtt-sn-gateway.cc     Priority queue + per-topic stats
│       └── cluster-aodv-mqtt.cc   Main simulation script
│
├── results/                   ← Simulation output CSVs
│   ├── cluster-aodv-nosink-results.csv
│   ├── mqtt-sn-results.csv
│   └── mqtt-sn-priority-results.csv
│
└── graphs/                    ← Generated comparison graphs
    ├── 01_pdr_comparison.png
    ├── 02_delay_comparison.png
    ├── ...
    └── 08_summary_dashboard.png
```

---

## 🔧 Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Total Nodes | 200 (180 sensors + 20 CH) |
| Area | 1000m × 1000m |
| WiFi | IEEE 802.11b Ad-Hoc |
| Propagation | LogDistance (exp=2.5) |
| Tx Power | 20 dBm (~250-300m range) |
| Routing | AODV (tuned for 200 nodes) |
| Application | MQTT-SN over UDP |
| MQTT Port | 1883 |
| Simulation Time | 100 seconds |
| Emergency Probability | 0.5% per publish |

### AODV Tuning

| Parameter | Default | Configured | Reason |
|-----------|---------|------------|--------|
| HelloInterval | 1s | 2s | Reduce overhead (200→100 Hello/sec) |
| ActiveRouteTimeout | 3s | 15s | Longer routes for static nodes |
| RreqRetries | 2 | 5 | More retries for large network |
| NetDiameter | 35 | 20 | Match network hop count |

---

## 📡 MQTT-SN Protocol

### Message Types

| Type | Code | Usage |
|------|------|-------|
| CONNECT | 0x04 | Sensor registers with gateway |
| CONNACK | 0x05 | Gateway confirms connection |
| PUBLISH | 0x0C | Sensor sends data |
| PUBACK | 0x0D | Gateway acknowledges (QoS>0) |
| DISCONNECT | 0x18 | Sensor disconnects |

### Priority System

| Level | QoS | Sensors | Behavior |
|-------|-----|---------|----------|
| CRITICAL (3) | - | Emergency alerts | Immediate processing |
| HIGH (2) | 2 | ECG | Must deliver, PUBACK required |
| MEDIUM (1) | 1 | Heart Rate | Important, PUBACK required |
| LOW (0) | 0 | Temperature | Best effort, no PUBACK |

---

## 🗺️ Roadmap

- [x] Phase 1: Cluster-based AODV simulation
- [x] Phase 2: MQTT-SN protocol integration
- [x] Phase 3: Priority-aware MQTT-SN with emergency detection
- [ ] Phase 3.2: Mobility model (moving patients)
- [ ] Phase 3.3: Different node count comparison (50/100/150/200)
- [ ] Phase 4: Security analysis (replay attack, spoofing, anomaly detection)
- [ ] Phase 5: Academic publication (IEEE/Elsevier)

---

## 👤 Author

**Amro Baseet**
- Sakarya University of Applied Sciences
- Computer Engineering — M.Sc.
- Supervisor: Assoc. Prof. Dr. İsmail Bütün
- GitHub: [amirbaseet](https://github.com/amirbaseet)

---

## 📚 References

1. C. Perkins et al., "AODV Routing," RFC 3561, 2003
2. A. Stanford-Clark, "MQTT-SN Protocol," IBM, 2013
3. ns-3 Network Simulator — https://www.nsnam.org/
4. OASIS, "MQTT Version 5.0," 2019
