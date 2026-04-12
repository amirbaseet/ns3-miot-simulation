# ns3-miot-simulation

## Performance Evaluation of Cluster-Based WSN-AODV and MQTT-SN Architectures for Medical IoT Using ns-3

A statistically validated ns-3 simulation study comparing two cluster-based Medical IoT communication architectures across 240 independent simulation runs (10 seeds per configuration, Welch t-tests).

- **Architecture A (WSN):** Cluster-based AODV routing with fixed-rate UDP transmission
- **Architecture B (MQTT-SN):** Priority-aware publish-subscribe with QoS differentiation

**Paper:** *Performance Evaluation of Cluster-Based WSN-AODV and MQTT-SN Architectures for Medical IoT Using ns-3* — submitted to SAUCIS (Sakarya University Journal of Computer and Information Sciences)

**SAVTEK 2026:** *Savunma Saha Sağlık Ağlarında Küme Tabanlı KAA-AODV ve MQTT-SN Mimarilerinin ns-3 ile Başarım Değerlendirmesi* — accepted

---

## Architecture

```
Architecture A — Traditional WSN (AODV + UDP):
  [Sensor] --OnOff 4kbps UDP--> [CH: UdpForwarder] --forward--> [Sink]

Architecture B — MQTT-SN Publish-Subscribe:
  [ECG  250ms/128B/QoS2]---+
  [HR   1s/64B/QoS1    ]---+--> [CH: MqttSnGateway] --MQTT-SN--> [MqttSnBroker]
  [Temp 5s/32B/QoS0    ]---+    (priority queue)
  [Emergency 0.5% prob ]---+
```

### Shared Protocol Stack

| Layer | Protocol |
|-------|----------|
| Application | WSN: OnOffApplication / MQTT-SN: Publish-Subscribe |
| Transport | UDP |
| Network | IPv4 + AODV (HelloInterval=2s, RreqRetries=5, ActiveRouteTimeout=15s) |
| MAC / PHY | IEEE 802.11b Ad-Hoc (11 Mbps, 20 dBm, ~300m range) |
| Propagation | LogDistance (exponent = 2.5) |

### MQTT-SN Sensor Types

| Type | Interval | Payload | QoS | Priority |
|------|----------|---------|-----|----------|
| ECG | 250 ms | 128 B | 2 | HIGH |
| Heart Rate | 1 s | 64 B | 1 | MEDIUM |
| Temperature | 5 s | 32 B | 0 | LOW |
| Emergency | 0.5% per publish | 128 B | 2 | CRITICAL |

---

## Experimental Results (10 seeds, Welch t-test)

All results are mean ± std over 10 independent random seeds. Statistical significance: * p<0.05, ** p<0.01, *** p<0.001, ns p≥0.05.

### Set 1 — No Broker (Application-Layer Isolation)

| Nodes | WSN PDR | MQTT-SN PDR | p(PDR) | WSN Delay | MQTT-SN Delay | p(Delay) |
|:-----:|:-------:|:-----------:|:------:|:---------:|:-------------:|:--------:|
| 50 | 84.1±11.3% | 88.7±8.6% | 0.3282 ns | 53.7±18.8 ms | 29.4±9.2 ms | 0.0028 ** |
| 100 | 99.1±0.9% | 99.0±0.9% | 0.7950 ns | 86.3±12.8 ms | 58.4±11.3 ms | 0.0001 *** |
| 150 | 98.3±0.7% | 99.5±0.7% | **0.0011 \*\*** | 111.2±11.5 ms | 64.1±18.3 ms | <0.0001 *** |
| 200 | 96.7±1.9% | 99.5±0.4% | **0.0011 \*\*** | 123.3±12.2 ms | 121.4±21.0 ms | 0.8122 ns |

### Set 2 — With Broker (Full End-to-End Architecture)

| Nodes | WSN PDR | MQTT-SN PDR | p(PDR) | WSN Delay | MQTT-SN Delay | p(Delay) |
|:-----:|:-------:|:-----------:|:------:|:---------:|:-------------:|:--------:|
| 50 | 84.6±11.2% | 85.4±14.0% | 0.8857 ns | 53.0±9.9 ms | 40.8±15.5 ms | 0.0546 ns |
| 100 | 94.8±4.3% | 90.0±7.7% | 0.1089 ns | 62.2±24.2 ms | 73.5±23.2 ms | 0.2990 ns |
| 150 | 82.2±2.7% | 76.3±3.1% | **0.0002 \*\*\*** | 124.7±21.8 ms | 151.5±27.1 ms | 0.0260 * |
| 200 | 67.4±8.3% | 63.4±6.8% | 0.2601 ns | 216.1±37.3 ms | 217.8±27.8 ms | 0.9077 ns |

### Set 3 — Equal Load, No Broker (Protocol Mechanism Isolation)

WSN sensors adopt the MQTT-SN heterogeneous traffic profile (ECG 4kbps, HR 512bps, Temp 51bps). MQTT-SN data is identical to Set 1.

| Nodes | WSN-Hetero PDR | MQTT-SN PDR | p(PDR) |
|:-----:|:--------------:|:-----------:|:------:|
| 50 | 84.3±11.8% | 88.7±8.6% | 0.3581 ns |
| 100 | 98.9±1.0% | 99.0±0.9% | 0.7876 ns |
| 150 | 98.9±0.5% | 99.5±0.7% | 0.0523 ns |
| 200 | 94.2±5.6% | 99.5±0.4% | **0.0149 \*** |

### Set 3b — Equal Load, With Broker (Gateway Overhead Under Congestion)

Same heterogeneous traffic as Set 3, broker active. MQTT-SN+broker data is identical to Set 2.

| Nodes | WSN-Hetero PDR | MQTT-SN PDR | p(PDR) |
|:-----:|:--------------:|:-----------:|:------:|
| 50 | 84.0±11.6% | 85.4±14.0% | 0.8114 ns |
| 100 | 93.7±5.2% | 90.0±7.7% | 0.2332 ns |
| 150 | 80.4±2.9% | 76.3±3.1% | **0.0066 \*\*** |
| 200 | 72.4±2.0% | 63.4±6.8% | **0.0022 \*\*** |

### Set 5 — Multi-Broker Hierarchy Sweep (200 nodes, 1 seed)

Two-tier broker architecture: N local tier-1 brokers + 1 root broker. Preliminary results.

| numLocalBrokers | Topology | PDR |
|:---------------:|:--------:|:---:|
| 1 | Single broker (baseline) | 73.4% |
| 2 | Two-tier (2 local + 1 root) | 73.0% |
| 4 | Two-tier (4 local + 1 root) | 74.5% |
| 5 | Two-tier (5 local + 1 root) | 73.3% |

**Finding:** PDR is flat across all broker counts (~73–74%). The bottleneck is the shared 802.11b wireless channel, not the broker architecture. Broker distribution alone does not recover performance at this scale.

---

## Key Findings

1. **MQTT-SN wins without broker** — Statistically significantly higher PDR at 150 and 200 nodes (p=0.0011). Significantly lower delay at 50–150 nodes.
2. **WSN wins with broker at 150 nodes** — Gateway overhead (1ms/packet + QoS ACK) amplifies single-sink congestion (p=0.0002).
3. **MQTT-SN protocol mechanisms are real** — Even under equal traffic load (Set 3), MQTT-SN still wins at 200 nodes (p=0.0149). The PDR advantage is not purely due to lower traffic volume.
4. **Broker inversion** — Set 3b reverses Set 3: with a broker, WSN-Hetero wins at both 150 and 200 nodes (p=0.0066, p=0.0022). Gateway overhead dominates under centralised congestion.
5. **Single-seed simulation is insufficient** — Preliminary single-seed runs showed MQTT-SN winning in Set 2. The 10-seed Welch t-test reversed this conclusion at 150 nodes. Multi-seed validation is essential.
6. **Broker distribution does not help** — Two-tier hierarchy with 1–5 local brokers produces flat PDR (~73–74%) at 200 nodes. Channel saturation is the limiting factor.

---

## Quick Start

### Requirements

- ns-3 v3.40 (important: v3.41 causes PDR=0% bug in ad-hoc mode)
- Python 3.8+ with: `pandas`, `matplotlib`, `scipy`, `numpy`

```bash
# Verify ns-3 version before running
cd ~/ns-3-dev && git log --oneline -1
```

### Build

```bash
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-mqtt
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-nosink

cp src/mqtt-sn/* ~/ns-3-dev/scratch/cluster-aodv-mqtt/
cp src/wsn/cluster-aodv-nosink.cc ~/ns-3-dev/scratch/cluster-aodv-nosink/

cd ~/ns-3-dev
./ns3 build
```

### Run Single Simulations

```bash
cd ~/ns-3-dev

# WSN — no sink
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20 --useSink=false --simTime=300"

# WSN — with sink
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20 --useSink=true --simTime=300"

# WSN — heterogeneous traffic (equal load)
./ns3 run "cluster-aodv-nosink --numRegular=200 --numCH=20 --useSink=false --hetero=true --simTime=300"

# MQTT-SN — no broker
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --numLocalBrokers=0 --simTime=300 --anim=false"

# MQTT-SN — single broker
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --numLocalBrokers=1 --simTime=300 --anim=false"

# MQTT-SN — two-tier hierarchy (4 local brokers + 1 root)
./ns3 run "cluster-aodv-mqtt --nSensors=200 --nCH=20 --numLocalBrokers=4 --simTime=300 --anim=false"
```

### Run All Statistical Experiments

```bash
cd ~/ns-3-dev
mkdir -p experiments/statistical experiments/hier

# Full 4-set comparison (240 runs, ~8h on 4-core machine)
tmux new-session -d -s experiments "bash ~/projects/ns3-miot-simulation/scripts/run-comparison.sh"
tmux attach -t experiments

# Multi-broker hierarchy sweep (Set 5, 40 runs)
tmux new-session -d -s set5 "bash ~/projects/ns3-miot-simulation/scripts/run-comparison.sh --set5-only"
```

### Analyze Results

```bash
cd ~/ns-3-dev
python3 ~/projects/ns3-miot-simulation/scripts/analyze_comparison.py
```

Generates 24 graphs (TR+EN) in `graphs/comparison/` and `graphs/hier/`, plus full statistical output with Welch t-test p-values.

---

## Command-Line Parameters

### cluster-aodv-mqtt (MQTT-SN)

| Parameter | Default | Description |
|-----------|---------|-------------|
| --nSensors | 200 | Number of sensor nodes |
| --nCH | 20 | Number of cluster heads |
| --numLocalBrokers | 1 | 0=no broker, 1=single broker, N≥2=two-tier hierarchy |
| --run | 1 | Random seed index |
| --simTime | 300 | Simulation time (s) |
| --anim | false | Generate NetAnim XML |
| --csv | auto | Output CSV filename |

### cluster-aodv-nosink (WSN)

| Parameter | Default | Description |
|-----------|---------|-------------|
| --numRegular | 200 | Number of sensor nodes |
| --numCH | 20 | Number of cluster heads |
| --useSink | false | Enable sink with forwarding |
| --hetero | false | Heterogeneous traffic rates (equal-load mode) |
| --run | 1 | Random seed index |
| --simTime | 300 | Simulation time (s) |
| --csv | auto | Output CSV filename |

---

## Project Structure

```
ns3-miot-simulation/
│
├── src/
│   ├── wsn/
│   │   └── cluster-aodv-nosink.cc       WSN: AODV + UDP + UdpForwarder + --hetero
│   └── mqtt-sn/
│       ├── mqtt-sn-header.h/cc          Packet format + 4-level priority
│       ├── mqtt-sn-publisher.h/cc       Sensor app + emergency detection
│       ├── mqtt-sn-gateway.h/cc         Gateway + priority queue + 1ms delay
│       ├── mqtt-sn-broker.h/cc          Broker + two-tier hierarchy support
│       └── cluster-aodv-mqtt.cc         Main simulation + --numLocalBrokers
│
├── experiments/
│   ├── statistical/                     240 CSVs (Sets 1, 2, 3, 3b)
│   │   ├── exp1_wsn_{50,100,150,200}_r{1-10}.csv
│   │   ├── exp1_mqtt_{50,100,150,200}_r{1-10}.csv
│   │   ├── exp2_wsn_{50,100,150,200}_r{1-10}.csv
│   │   ├── exp2_mqtt_{50,100,150,200}_r{1-10}.csv
│   │   ├── exp3_wsn_hetero_{50,100,150,200}_r{1-10}.csv
│   │   └── exp3b_wsn_hetero_broker_{50,100,150,200}_r{1-10}.csv
│   └── hier/                            Multi-broker sweep CSVs (Set 5)
│       └── exp_hier_lb{1,2,4,5}_200_r{1-10}.csv
│
├── graphs/
│   ├── comparison/                      24 analysis graphs (TR+EN)
│   └── hier/                            Multi-broker hierarchy graphs
│
├── scripts/
│   ├── analyze_comparison.py            Main analysis: Welch t-tests + 24 graphs
│   └── run-comparison.sh                Full experiment runner (Sets 1-3b + Set 5)
│
└── README.md
```

---

## Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Simulation area | 1000 m × 1000 m |
| Wireless standard | IEEE 802.11b Ad-Hoc, 11 Mbps |
| Propagation model | LogDistance (exponent = 2.5) |
| Transmit power | 20 dBm (~300 m range) |
| Routing | AODV (HelloInterval=2s, RreqRetries=5, ActiveRouteTimeout=15s) |
| Simulation duration | 300 s |
| Node start (warmup) | Staggered 5–45 s per node |
| Random seeds | 10 independent seeds per configuration |
| Node counts | 50, 100, 150, 200 sensors |
| CH ratio | 10% (fixed grid placement) |
| Statistical test | Welch's t-test (equal_var=False) |
| Energy model | BasicEnergySource: sensors 2.0J, CHs 5.0J |
| Radio currents | Tx=0.346A, Rx=0.285A, Idle=0.248A (both architectures) |

---

## Roadmap

- [x] Phase 1: Cluster-based AODV (Traditional WSN)
- [x] Phase 2: MQTT-SN protocol stack from scratch
- [x] Phase 3: Priority-aware gateway + emergency detection
- [x] Phase 4: Broker/Sink + UdpForwarder + --hetero flag
- [x] Statistical comparison: 10 seeds + Welch t-test (Sets 1, 2, 3, 3b)
- [x] Multi-broker hierarchy: two-tier topology (Set 5)
- [x] Energy model: standardised radio currents (both architectures)
- [x] SAUCIS journal paper (English, submitted)
- [ ] Set 5: 10-seed statistical confirmation of multi-broker findings
- [ ] Energy analysis: comparative cross-architecture energy plots
- [ ] IEEE 802.15.4 / BLE physical layer evaluation
- [ ] Real testbed validation

---

## Citation

If you use this code or data in your research, please cite:

```
A. Baseet and I. Butun, "Performance Evaluation of Cluster-Based WSN-AODV
and MQTT-SN Architectures for Medical IoT Using ns-3,"
SAUCIS, 2026. (under review)
https://github.com/amirbaseet/ns3-miot-simulation
```

---

## Author

**Amro Baseet**
MSc Computer Engineering, Sakarya University
Supervisor: Assoc. Prof. Dr. İsmail Bütün

---

## References

1. C. Perkins et al., "Ad Hoc On-Demand Distance Vector (AODV) Routing," IETF RFC 3561, 2003
2. A. Stanford-Clark and H. L. Truong, "MQTT for Sensor Networks (MQTT-SN) v1.2," OASIS, 2013
3. G. F. Riley and T. R. Henderson, "The ns-3 Network Simulator," Springer, 2010
4. OASIS, "MQTT Version 5.0," 2019
