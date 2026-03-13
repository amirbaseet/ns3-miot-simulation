# ns3-miot-simulation

## Performance Comparison of Traditional WSN and MQTT-SN Publish-Subscribe Architecture in Cluster-Based MIoT Networks Using ns-3

A comprehensive ns-3 simulation comparing two communication architectures for Medical Internet of Things:
- **Scenario A (WSN):** Traditional AODV + UDP constant-rate data push
- **Scenario B (MQTT-SN):** Priority-aware publish-subscribe with heterogeneous sensor traffic

---

## Architecture

```
Scenario A — Traditional WSN:
  [Sensor] --OnOff 4kbps UDP--> [CH: PacketSink/UdpForwarder] --forward--> [Sink]

Scenario B — MQTT-SN:
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

### MQTT-SN Node Types

| Type | Count | Interval | Payload | Priority |
|------|-------|----------|---------|----------|
| ECG Sensors | nSensors/3 | 250ms | 128B | HIGH (QoS=2) |
| Heart Rate | nSensors/3 | 1s | 64B | MEDIUM (QoS=1) |
| Temperature | nSensors/3 | 5s | 32B | LOW (QoS=0) |
| Emergency | Random 0.5% | Immediate | 128B | CRITICAL |
| Gateway (CH) | nCH | - | - | Priority Queue |
| Broker (Sink) | 1 | - | - | Central collection |

---

## Experimental Results

### Experiment 1: WSN vs MQTT-SN — No Broker (Application Layer Only)

| Nodes | WSN PDR | MQTT-SN PDR | WSN Delay | MQTT-SN Delay | Winner |
|:-----:|:-------:|:-----------:|:---------:|:-------------:|:------:|
| 50 | 70.22% | **88.55%** | 66.22ms | **58.09ms** | MQTT-SN |
| 100 | **99.89%** | 98.32% | 56.44ms | **64.15ms** | WSN |
| 150 | 96.63% | **98.97%** | 119.57ms | **55.17ms** | MQTT-SN |
| 200 | 96.36% | **99.97%** | 181.46ms | **19.36ms** | MQTT-SN |

### Experiment 2: WSN vs MQTT-SN — With Broker (Full Architecture)

| Nodes | WSN PDR | MQTT-SN PDR | WSN Delay | MQTT-SN Delay | Winner |
|:-----:|:-------:|:-----------:|:---------:|:-------------:|:------:|
| 50 | 66.47% | **87.33%** | **25.13ms** | 80.84ms | MQTT-SN |
| 100 | **99.68%** | 81.73% | **87.40ms** | 87.05ms | WSN |
| 150 | **79.30%** | 78.83% | **82.95ms** | 103.21ms | Tie |
| 200 | **71.11%** | 70.39% | **172.88ms** | 192.41ms | Tie |

### Experiment 3: Traffic Load Impact (180 nodes, broker enabled)

| Load | ECG/HR/Temp | Tx Packets | PDR | Delay |
|:----:|:-----------:|:----------:|:---:|:-----:|
| Low | 20/20/140 | 92K | 74.81% | 148ms |
| Medium | 60/60/60 | 220K | 71.82% | 137ms |
| High | 140/20/20 | 505K | 65.45% | 253ms |

### Experiment 4: Mobility Impact (180 nodes, broker enabled)

| Speed | Scenario | PDR | Delay | Dead Flows |
|:-----:|:--------:|:---:|:-----:|:----------:|
| 0 m/s | Static | 71.50% | 131ms | 211 |
| 0.5 m/s | Slow walking | 73.60% | 79ms | 470 |
| 1.5 m/s | Normal walking | 64.49% | 121ms | 1,242 |
| 3.0 m/s | Running | 56.30% | 112ms | 2,983 |

### Experiment 5: Energy Consumption (180 sensors + 20 CHs, 100s)

| Node Type | Initial | Consumed | Remaining |
|:---------:|:-------:|:--------:|:---------:|
| Sensors (180) | 2.0 J each | 72.4% | 0.55 J avg |
| CHs (20) | 5.0 J each | 72.1% | 1.40 J avg |

### Experiment 6: Priority-Aware MQTT-SN (200 nodes, no broker)

| Metric | Value |
|--------|-------|
| PDR | 99.97% |
| Average Delay | 0.87 ms |
| Dead Flows | 10 |
| Emergency Alerts | 152 detected |

---

## Key Findings

1. **MQTT-SN outperforms WSN in broker-free configurations** — 99.97% PDR vs 96.36% at 200 nodes, with 9.4x lower delay (19ms vs 181ms)
2. **Heterogeneous traffic reduces network load by 62%** — temperature sensors at 5s intervals vs constant 4kbps in WSN
3. **Broker bottleneck equalizes performance** — at 200 nodes with broker, both converge to ~70% PDR
4. **Mobility degrades AODV performance** — PDR drops from 71.5% to 56.3% at walking speed (3 m/s), dead flows increase 14x
5. **ECG ratio dominates traffic load** — increasing ECG from 20 to 140 nodes increases traffic 5.5x
6. **WiFi idle power dominates energy** — uniform 72% consumption regardless of sensor type

---

## Quick Start

### Build

```bash
# Copy simulation files
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-mqtt
cp phase4-broker/mqtt-sn/* ~/ns-3-dev/scratch/cluster-aodv-mqtt/
cp phase1/cluster-aodv-nosink.cc ~/ns-3-dev/scratch/cluster-aodv-nosink/cluster-aodv-nosink.cc

cd ~/ns-3-dev
./ns3 configure --enable-examples --enable-tests
./ns3 build
```

### Run Individual Simulations

```bash
# WSN — no sink
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20"

# WSN — with sink (real forwarding)
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20 --useSink=true"

# MQTT-SN — no broker
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --broker=false"

# MQTT-SN — with broker
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --broker=true"

# MQTT-SN — with mobility
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=true --speed=1.5"

# MQTT-SN — custom traffic load
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --nECG=140 --nHR=20 --broker=true"
```

### Run All Experiments

```bash
# Fair comparison: 16 simulations (WSN vs MQTT-SN, broker/no-broker, 50-200 nodes)
chmod +x run-comparison.sh && ./run-comparison.sh

# Traffic load: Low/Medium/High ECG ratio
chmod +x run-traffic-experiments.sh && ./run-traffic-experiments.sh

# Mobility: Static/0.5/1.5/3.0 m/s
chmod +x run-mobility-experiments.sh && ./run-mobility-experiments.sh

# Scalability: WSN vs MQTT-SN at 50/100/150/200 nodes
chmod +x run-experiments.sh && ./run-experiments.sh
```

### Analyze Results

```bash
# Main comparison (16 experiments, 11 graphs)
python3 analyze_comparison.py

# Individual analyses
python3 analyze_scalability.py
python3 analyze_traffic.py
python3 analyze_mobility.py
python3 analyze_energy.py experiments/energy_test.csv.energy.csv
python3 compare_phases.py
python3 analyze_results.py results/mqtt-sn-priority-results.csv
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
| --broker | true | Enable broker/sink node |
| --mobility | false | Enable RandomWaypoint mobility |
| --speed | 1.5 | Mobility speed (m/s) |
| --simTime | 100 | Simulation duration (seconds) |
| --anim | false | Generate NetAnim XML |
| --verbose | false | Print MQTT-SN messages |
| --csv | auto | Output CSV filename |

### cluster-aodv-nosink (Traditional WSN)

| Parameter | Default | Description |
|-----------|---------|-------------|
| --numRegular | 180 | Number of sensor nodes |
| --numCH | 20 | Number of cluster heads |
| --useSink | false | Enable sink with real forwarding |
| --simTime | 100 | Simulation duration |
| --csv | auto | Output CSV filename |

---

## Project Structure

```
ns3-miot-simulation/
├── README.md
├── HOW_TO_RUN.md
├── COMPARISON_DESIGN.md              # Experiment design document
├── MIoT_Report_Updated.docx          # Full project report
│
├── phase1/                            # Scenario A: Traditional WSN
│   ├── cluster-aodv-nosink.cc           AODV + UDP + UdpForwarder
│   └── cluster-aodv-sim.cc             (legacy with-sink version)
│
├── phase3/mqtt-sn/                    # Priority MQTT-SN (no broker)
│
├── phase4-broker/mqtt-sn/             # Scenario B: Full MQTT-SN
│   ├── mqtt-sn-header.h/cc              Packet format + priorities
│   ├── mqtt-sn-publisher.h/cc           Sensor app + emergency
│   ├── mqtt-sn-gateway.h/cc             Gateway + priority queue + forwarding
│   ├── mqtt-sn-broker.h/cc              Broker/sink application
│   └── cluster-aodv-mqtt.cc             Main simulation (all features)
│
├── experiments/                        # All experiment CSV results
│   ├── comparison/                       16 fair comparison CSVs
│   │   ├── exp1_wsn_50..200.csv           Set 1: No broker
│   │   ├── exp1_mqtt_50..200.csv
│   │   ├── exp2_wsn_50..200.csv           Set 2: With broker
│   │   └── exp2_mqtt_50..200.csv
│   ├── traffic_low/medium/high.csv       Traffic load experiments
│   ├── mobility_static/slow/normal/fast.csv  Mobility experiments
│   └── energy_test.csv.energy.csv        Energy data
│
├── results/                            # Phase comparison CSVs
├── graphs/                             # Generated analysis graphs
│   ├── comparison/                       11 WSN vs MQTT-SN graphs
│   ├── scalability/                      7 scalability graphs
│   ├── traffic/                          6 traffic load graphs
│   ├── mobility/                         6 mobility graphs
│   └── energy/                           4 energy graphs
│
├── diagrams/                           # UML diagrams (Mermaid)
│   ├── 01_class_diagram.mermaid
│   ├── 02_sequence_diagram.mermaid
│   ├── 03_activity_diagram.mermaid
│   ├── 04_network_architecture.mermaid
│   └── 05_gateway_processing.mermaid
│
├── analyze_comparison.py               # Main: WSN vs MQTT-SN (11 graphs)
├── analyze_scalability.py              # Scalability analysis
├── analyze_traffic.py                  # Traffic load analysis
├── analyze_mobility.py                 # Mobility analysis
├── analyze_energy.py                   # Energy analysis
├── analyze_results.py                  # Single CSV analyzer
├── compare_phases.py                   # Phase 1/2/3/4 comparison
│
├── run-comparison.sh                   # 16 fair comparison experiments
├── run-experiments.sh                  # Scalability experiments
├── run-traffic-experiments.sh          # Traffic load experiments
└── run-mobility-experiments.sh         # Mobility experiments
```

---

## Roadmap

- [x] Phase 1: Cluster-based AODV (Traditional WSN)
- [x] Phase 2: MQTT-SN protocol integration
- [x] Phase 3: Priority-aware MQTT-SN + emergency detection
- [x] Phase 4: Broker/Sink node (full pipeline)
- [x] Fair Comparison: WSN vs MQTT-SN (broker + no-broker)
- [x] Experiment: Scalability (50/100/150/200 nodes)
- [x] Experiment: Traffic load (Low/Medium/High ECG)
- [x] Experiment: Mobility (Static/0.5/1.5/3.0 m/s)
- [x] Experiment: Energy consumption model
- [x] UdpForwarder: Real CH forwarding for WSN
- [ ] Security analysis (replay attack, spoofing)
- [ ] Alternative routing (OLSR, DSDV comparison)
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
5. W. Heinzelman et al., "LEACH," HICSS, 2000
