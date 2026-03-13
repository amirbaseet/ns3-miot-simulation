# ns3-miot-simulation

## Performance Comparison of Traditional WSN and MQTT-SN Publish-Subscribe Architecture in Cluster-Based MIoT Networks Using ns-3

A comprehensive ns-3 simulation comparing two communication architectures for Medical Internet of Things:
- **Scenario A (WSN):** Traditional AODV + UDP constant-rate data push
- **Scenario B (MQTT-SN):** Priority-aware publish-subscribe with heterogeneous sensor traffic

---

## Architecture

```
Scenario A - Traditional WSN:
  [Sensor] --OnOff 4kbps UDP--> [CH: UdpForwarder] --forward--> [Sink]

Scenario B - MQTT-SN:
  [ECG 250ms]---+
  [HR  1s  ]----+--> [CH: Gateway + Priority Queue] --MQTT-SN--> [Broker]
  [Temp 5s ]---+
```

### Protocol Stack (Same for Both)

| Layer | Protocol |
|-------|----------|
| Application | WSN: OnOff / MQTT-SN: Publish-Subscribe |
| Transport | UDP |
| Network | IPv4 + AODV (tuned for 200 nodes) |
| MAC / PHY | IEEE 802.11b Ad-Hoc (11 Mbps, 20 dBm) |

### MQTT-SN Sensor Types

| Type | Interval | Payload | Priority |
|------|----------|---------|----------|
| ECG | 250ms | 128B | HIGH (QoS=2) |
| Heart Rate | 1s | 64B | MEDIUM (QoS=1) |
| Temperature | 5s | 32B | LOW (QoS=0) |
| Emergency | Random 0.5% | 128B | CRITICAL |

---

## Experimental Results

### Experiment 1: WSN vs MQTT-SN - No Broker (Application Layer)

| Nodes | WSN PDR | MQTT-SN PDR | WSN Delay | MQTT-SN Delay | Winner |
|:-----:|:-------:|:-----------:|:---------:|:-------------:|:------:|
| 50 | 70.22% | **88.55%** | 66ms | **58ms** | MQTT-SN |
| 100 | **99.89%** | 98.32% | 56ms | **64ms** | WSN |
| 150 | 96.63% | **98.97%** | 119ms | **55ms** | MQTT-SN |
| 200 | 96.36% | **99.97%** | 181ms | **19ms** | MQTT-SN |

### Experiment 2: WSN vs MQTT-SN - With Broker (Full Architecture)

| Nodes | WSN PDR | MQTT-SN PDR | WSN Delay | MQTT-SN Delay | Winner |
|:-----:|:-------:|:-----------:|:---------:|:-------------:|:------:|
| 50 | 66.47% | **87.33%** | **25ms** | 80ms | MQTT-SN |
| 100 | **99.68%** | 81.73% | **87ms** | 87ms | WSN |
| 150 | **79.30%** | 78.83% | **82ms** | 103ms | Tie |
| 200 | **71.11%** | 70.39% | **172ms** | 192ms | Tie |

### Experiment 3: Traffic Load (180 nodes, broker)

| Load | ECG/HR/Temp | Tx Packets | PDR | Delay |
|:----:|:-----------:|:----------:|:---:|:-----:|
| Low | 20/20/140 | 92K | 74.81% | 148ms |
| Medium | 60/60/60 | 220K | 71.82% | 137ms |
| High | 140/20/20 | 505K | 65.45% | 253ms |

### Experiment 4: Mobility (180 nodes, broker)

| Speed | Scenario | PDR | Dead Flows |
|:-----:|:--------:|:---:|:----------:|
| 0 m/s | Static | 71.50% | 211 |
| 0.5 m/s | Slow walking | 73.60% | 470 |
| 1.5 m/s | Normal walking | 64.49% | 1,242 |
| 3.0 m/s | Running | 56.30% | 2,983 |

### Experiment 5: Energy (180 sensors + 20 CHs)

| Node Type | Initial | Consumed | Remaining |
|:---------:|:-------:|:--------:|:---------:|
| Sensors | 2.0 J each | 72.4% | 0.55 J avg |
| CHs | 5.0 J each | 72.1% | 1.40 J avg |

### Experiment 6: Priority MQTT-SN (200 nodes, no broker)

| Metric | Value |
|--------|-------|
| PDR | 99.97% |
| Delay | 0.87 ms |
| Emergency Alerts | 152 |

---

## Key Findings

1. **MQTT-SN outperforms WSN without broker** - 99.97% vs 96.36% PDR at 200 nodes, 9.4x lower delay
2. **Heterogeneous traffic reduces load by 62%** - temperature at 5s vs constant 4kbps
3. **Broker bottleneck equalizes performance** - both converge to ~70% PDR at 200 nodes
4. **Mobility degrades AODV** - PDR drops to 56.3% at 3 m/s, dead flows increase 14x
5. **ECG ratio dominates traffic** - 140 ECG nodes create 5.5x more traffic than 20
6. **WiFi idle power dominates energy** - uniform 72% consumption regardless of sensor type

---

## Quick Start

### Build

```bash
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-mqtt
cp src/mqtt-sn/* ~/ns-3-dev/scratch/cluster-aodv-mqtt/
cp src/wsn/cluster-aodv-nosink.cc ~/ns-3-dev/scratch/cluster-aodv-nosink/cluster-aodv-nosink.cc
cd ~/ns-3-dev
./ns3 build
```

### Run Simulations

```bash
# WSN - no sink
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20"

# WSN - with sink (real forwarding)
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20 --useSink=true"

# MQTT-SN - no broker
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --broker=false"

# MQTT-SN - with broker
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --broker=true"

# MQTT-SN - with mobility
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=true --speed=1.5"

# MQTT-SN - custom traffic load
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --nECG=140 --nHR=20 --broker=true"
```

### Run All Experiments

```bash
cd ~/ns-3-dev
cp ~/projects/ns3-miot-simulation/scripts/run-*.sh .

# Fair comparison (16 simulations)
chmod +x run-comparison.sh && ./run-comparison.sh

# Traffic / Mobility / Scalability
chmod +x run-traffic-experiments.sh && ./run-traffic-experiments.sh
chmod +x run-mobility-experiments.sh && ./run-mobility-experiments.sh
chmod +x run-experiments.sh && ./run-experiments.sh
```

### Analyze Results

```bash
cd ~/projects/ns3-miot-simulation

# Main comparison (11 graphs)
python3 scripts/analyze_comparison.py

# Individual analyses
python3 scripts/analyze_scalability.py
python3 scripts/analyze_traffic.py
python3 scripts/analyze_mobility.py
python3 scripts/analyze_energy.py experiments/energy/energy_test.csv.energy.csv
```

---

## Command-Line Parameters

### cluster-aodv-mqtt (MQTT-SN)

| Parameter | Default | Description |
|-----------|---------|-------------|
| --nSensors | 180 | Number of sensor nodes |
| --nCH | 20 | Number of cluster heads |
| --nECG | 0 (auto) | ECG sensors (0 = nSensors/3) |
| --nHR | 0 (auto) | HR sensors (0 = nSensors/3) |
| --broker | true | Enable broker/sink |
| --mobility | false | Enable RandomWaypoint |
| --speed | 1.5 | Mobility speed (m/s) |
| --simTime | 100 | Simulation time (s) |
| --anim | false | NetAnim output |
| --verbose | false | Print MQTT-SN messages |
| --csv | auto | Output CSV filename |

### cluster-aodv-nosink (WSN)

| Parameter | Default | Description |
|-----------|---------|-------------|
| --numRegular | 180 | Number of sensor nodes |
| --numCH | 20 | Number of cluster heads |
| --useSink | false | Enable sink with real forwarding |
| --simTime | 100 | Simulation time (s) |
| --csv | auto | Output CSV filename |

---

## Project Structure

```
ns3-miot-simulation/
│
├── src/                              # Source code (latest version)
│   ├── wsn/                            Scenario A: Traditional WSN
│   │   └── cluster-aodv-nosink.cc        AODV + UDP + UdpForwarder
│   └── mqtt-sn/                        Scenario B: MQTT-SN
│       ├── mqtt-sn-header.h/cc           Packet format + priority levels
│       ├── mqtt-sn-publisher.h/cc        Sensor app + emergency detection
│       ├── mqtt-sn-gateway.h/cc          Gateway + priority queue + forwarding
│       ├── mqtt-sn-broker.h/cc           Broker/sink application
│       └── cluster-aodv-mqtt.cc          Main simulation
│
├── archive/                          # Historical phase versions
│   ├── phase1-baseline/                Original WSN code
│   └── phase3-priority/                Priority MQTT-SN (no broker)
│
├── experiments/                      # All experiment results
│   ├── comparison/                     16 fair comparison CSVs
│   │   ├── exp1_wsn_50..200.csv          Set 1: No broker
│   │   ├── exp1_mqtt_50..200.csv
│   │   ├── exp2_wsn_50..200.csv          Set 2: With broker
│   │   └── exp2_mqtt_50..200.csv
│   ├── traffic/                        Low/Medium/High ECG ratio
│   ├── mobility/                       Static/Slow/Normal/Fast
│   └── energy/                         Energy consumption data
│
├── results/                          # Phase comparison CSVs
│
├── graphs/                           # Generated analysis graphs
│   ├── comparison/                     11 WSN vs MQTT-SN graphs
│   ├── scalability/                    7 scalability graphs
│   ├── traffic/                        6 traffic load graphs
│   ├── mobility/                       6 mobility graphs
│   └── energy/                         4 energy graphs
│
├── diagrams/                         # UML diagrams (Mermaid)
│   ├── 01_class_diagram.mermaid
│   ├── 02_sequence_diagram.mermaid
│   ├── 03_activity_diagram.mermaid
│   ├── 04_network_architecture.mermaid
│   └── 05_gateway_processing.mermaid
│
├── scripts/                          # Analysis and experiment scripts
│   ├── analyze_comparison.py           WSN vs MQTT-SN (11 graphs)
│   ├── analyze_scalability.py          Scalability analysis
│   ├── analyze_traffic.py              Traffic load analysis
│   ├── analyze_mobility.py             Mobility analysis
│   ├── analyze_energy.py               Energy analysis
│   ├── analyze_results.py              Single CSV analyzer
│   ├── compare_phases.py               Phase comparison
│   ├── run-comparison.sh               16 fair comparison experiments
│   ├── run-experiments.sh              Scalability experiments
│   ├── run-traffic-experiments.sh      Traffic experiments
│   └── run-mobility-experiments.sh     Mobility experiments
│
├── README.md                         # This file
├── HOW_TO_RUN.md                     # Detailed run instructions
├── COMPARISON_DESIGN.md              # Experiment design document
└── MIoT_Report_Updated.docx          # Full project report
```

---

## Roadmap

- [x] Phase 1: Cluster-based AODV (Traditional WSN)
- [x] Phase 2: MQTT-SN protocol integration
- [x] Phase 3: Priority-aware MQTT-SN + emergency detection
- [x] Phase 4: Broker/Sink + UdpForwarder
- [x] Fair Comparison: WSN vs MQTT-SN (broker + no-broker)
- [x] Scalability experiments (50/100/150/200 nodes)
- [x] Traffic load experiments (Low/Medium/High ECG)
- [x] Mobility experiments (Static/0.5/1.5/3.0 m/s)
- [x] Energy consumption model
- [ ] Security analysis (replay attack, spoofing)
- [ ] Alternative routing (OLSR, DSDV)
- [ ] Multi-sink architecture
- [ ] Academic publication (IEEE/Elsevier)

---

## Author

**Amro Baseet**
- Sakarya University of Applied Sciences
- Computer Engineering, M.Sc.
- Supervisor: Assoc. Prof. Dr. Ismail Butun
- Funded by TUBITAK BIDEB

## References

1. C. Perkins et al., "AODV Routing," RFC 3561, 2003
2. A. Stanford-Clark, "MQTT-SN Protocol," IBM, 2013
3. ns-3 Network Simulator, https://www.nsnam.org/
4. OASIS, "MQTT Version 5.0," 2019
