# ns3-miot-simulation

## Cluster-Based AODV with Priority-Aware MQTT-SN for Medical IoT

A comprehensive ns-3 network simulation comparing Traditional WSN vs MQTT-SN publish-subscribe architecture for Medical Internet of Things. Includes scalability, traffic load, mobility, and energy consumption experiments.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    1000m x 1000m Area                        │
│                                                              │
│   [ECG]──┐         [HR]──┐          [Temp]──┐               │
│   [ECG]──┼──> [Gateway] ──┼──> [BROKER/SINK] <── [Gateway]  │
│   [ECG]──┘         [HR]──┘          [Temp]──┘               │
│                                                              │
│   Data Flow: Sensor -> Gateway (CH) -> Broker (Sink)         │
│   Routing: AODV | Transport: UDP | App: MQTT-SN              │
│   Priority: ECG=HIGH > HR=MEDIUM > Temp=LOW > Emergency=CRIT │
└─────────────────────────────────────────────────────────────┘
```

### Protocol Stack

| Layer | Protocol |
|-------|----------|
| Application | MQTT-SN (Publish/Subscribe + Priority Queue) |
| Transport | UDP (Port 1883 sensor to GW, 1884 GW to Broker) |
| Network | IPv4 + AODV (tuned for 200 nodes) |
| MAC / PHY | IEEE 802.11b Ad-Hoc (11 Mbps, 20 dBm) |

### Node Types

| Type | Count | Role | Priority |
|------|-------|------|----------|
| ECG Sensors | 60 | Publish every 250ms, 128B | HIGH (QoS=2) |
| Heart Rate Sensors | 60 | Publish every 1s, 64B | MEDIUM (QoS=1) |
| Temperature Sensors | 60 | Publish every 5s, 32B | LOW (QoS=0) |
| Cluster Heads (Gateway) | 20 | Priority queue + forward to broker | - |
| Broker (Sink) | 1 | Central data collection | - |

---

## Experiments and Results

### Experiment 1: Scalability (WSN vs MQTT-SN)

Same network, different node counts (50/100/150/200):

| Nodes | WSN PDR | MQTT-SN PDR | WSN Delay | MQTT-SN Delay |
|:-----:|:-------:|:-----------:|:---------:|:-------------:|
| 50 | 84.33% | 73.36% | 6.25 ms | 2.63 ms |
| 100 | 97.95% | 99.66% | 6.37 ms | 3.94 ms |
| 150 | 99.04% | 76.41% | 10.43 ms | 108.08 ms |
| 200 | 97.42% | 69.81% | 32.57 ms | 112.67 ms |

### Experiment 2: Traffic Load Impact

Same network (180 nodes), different ECG sensor ratios:

| Load | ECG/HR/Temp | Tx Packets | PDR | Delay |
|:----:|:-----------:|:----------:|:---:|:-----:|
| Low | 20/20/140 | 92K | 74.81% | 148 ms |
| Medium | 60/60/60 | 220K | 71.82% | 137 ms |
| High | 140/20/20 | 505K | 65.45% | 253 ms |

### Experiment 3: Mobility Impact

Same network (180 nodes), different patient movement speeds:

| Speed | Scenario | PDR | Delay | Dead Flows |
|:-----:|:--------:|:---:|:-----:|:----------:|
| 0 m/s | Static (bedridden) | 71.50% | 131 ms | 211 |
| 0.5 m/s | Slow walking | 73.60% | 79 ms | 470 |
| 1.5 m/s | Normal walking | 64.49% | 121 ms | 1,242 |
| 3.0 m/s | Running/emergency | 56.30% | 112 ms | 2,983 |

### Experiment 4: Energy Consumption

180 sensors (2.0J battery) + 20 CHs (5.0J battery):

| Node Type | Initial | Consumed | Remaining | Dead |
|:---------:|:-------:|:--------:|:---------:|:----:|
| Sensors | 360 J | 260.66 J (72.4%) | 99.34 J | 0 |
| CHs | 100 J | 72.06 J (72.1%) | 27.94 J | 0 |

---

## Quick Start

### Prerequisites

```bash
# ns-3-dev installed at ~/ns-3-dev
pip install matplotlib pandas --break-system-packages
```

### Build

```bash
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-mqtt
cp phase4-broker/mqtt-sn/* ~/ns-3-dev/scratch/cluster-aodv-mqtt/
cp phase1/cluster-aodv-nosink.cc ~/ns-3-dev/scratch/cluster-aodv-nosink/
cd ~/ns-3-dev
./ns3 build
```

### Run Simulations

```bash
# Traditional WSN (Scenario A)
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20"

# MQTT-SN with Broker (Scenario B)
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true"

# With mobility
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=true --speed=1.5"

# Custom traffic load
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --nECG=140 --nHR=20 --broker=true"
```

### Run All Experiments

```bash
chmod +x run-experiments.sh && ./run-experiments.sh
chmod +x run-traffic-experiments.sh && ./run-traffic-experiments.sh
chmod +x run-mobility-experiments.sh && ./run-mobility-experiments.sh
```

### Analyze Results

```bash
python3 compare_phases.py
python3 analyze_scalability.py
python3 analyze_traffic.py
python3 analyze_mobility.py
python3 analyze_energy.py experiments/energy_test.csv.energy.csv
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
| --simTime | 100 | Simulation duration |
| --csv | auto | Output CSV filename |

---

## Project Structure

```
ns3-miot-simulation/
├── README.md
├── HOW_TO_RUN.md
├── phase1/                          # Traditional WSN (Scenario A)
│   ├── cluster-aodv-nosink.cc
│   └── cluster-aodv-sim.cc
├── phase3/mqtt-sn/                  # Priority MQTT-SN (no broker)
├── phase4-broker/mqtt-sn/           # Full pipeline (Scenario B)
│   ├── mqtt-sn-header.h/cc            Packet format + priority
│   ├── mqtt-sn-publisher.h/cc         Sensor app + emergency
│   ├── mqtt-sn-gateway.h/cc           CH gateway + broker forwarding
│   ├── mqtt-sn-broker.h/cc            Sink/broker application
│   └── cluster-aodv-mqtt.cc           Main simulation
├── results/                         # Phase comparison CSVs
├── experiments/                     # All experiment CSVs
├── graphs/                          # Generated analysis graphs
│   ├── scalability/                   WSN vs MQTT-SN (7 graphs)
│   ├── traffic/                       Traffic load (6 graphs)
│   ├── mobility/                      Mobility (6 graphs)
│   └── energy/                        Energy (4 graphs)
├── diagrams/                        # UML diagrams (Mermaid)
├── analyze_results.py               # Single phase analyzer
├── compare_phases.py                # Phase comparison
├── analyze_scalability.py           # WSN vs MQTT-SN
├── analyze_traffic.py               # Traffic load
├── analyze_mobility.py              # Mobility impact
├── analyze_energy.py                # Energy consumption
├── run-experiments.sh               # Scalability experiments
├── run-traffic-experiments.sh       # Traffic experiments
└── run-mobility-experiments.sh      # Mobility experiments
```

---

## Key Findings

1. MQTT-SN reduces traffic by 88% compared to constant-rate WSN using heterogeneous sensor intervals
2. Priority queue ensures critical ECG data is processed first before temperature readings
3. Broker bottleneck: Adding a central sink drops PDR due to 20 CHs forwarding simultaneously
4. Mobility degrades performance: PDR drops from 71.5% (static) to 56.3% (3 m/s) as AODV routes break
5. Higher ECG ratio increases traffic load: PDR drops from 74.8% (20 ECG) to 65.4% (140 ECG)
6. Energy consumption is uniform at about 72% across all node types in 100s simulation

---

## Roadmap

- [x] Phase 1: Cluster-based AODV (Traditional WSN)
- [x] Phase 2: MQTT-SN protocol integration
- [x] Phase 3: Priority-aware MQTT-SN with emergency detection
- [x] Phase 4: Broker/Sink node (full pipeline)
- [x] Experiment: Scalability (50/100/150/200 nodes)
- [x] Experiment: Traffic load (Low/Medium/High ECG)
- [x] Experiment: Mobility (Static/0.5/1.5/3.0 m/s)
- [x] Experiment: Energy consumption model
- [ ] Security analysis (replay attack, spoofing)
- [ ] Alternative routing comparison (OLSR, DSDV)
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
