# SENIOR REVIEW: MIoT Simulation Project
## WSN vs MQTT-SN Comparison Using ns-3

**Reviewer perspective:** Senior network simulation researcher, ns-3 expert
**Date:** March 2026

---

## 1. EXECUTIVE SUMMARY

This is a **solid M.Sc.-level simulation project** that demonstrates competence in ns-3 development, protocol design, and experimental methodology. The dual-comparison approach (with and without broker) is well-conceived, and the breadth of experiments (scalability, traffic load, mobility, energy) exceeds typical thesis requirements. However, several methodological issues — primarily the single random seed, unequal traffic loads between scenarios, and the simplified energy model — would need to be addressed before journal submission. The work is **thesis-ready with minor revisions** and **conditionally publishable** in a conference or lower-tier journal after addressing statistical rigor.

---

## 2. STRENGTHS

- **Well-structured dual comparison:** Testing both application-layer-only (no broker) and full-architecture (with broker) configurations is methodologically sound and directly addresses the supervisor's requirement.
- **Custom MQTT-SN implementation:** Building MqttSnHeader, MqttSnPublisher, MqttSnGateway, and MqttSnBroker as proper ns-3 Application subclasses shows strong C++ and ns-3 understanding.
- **Real forwarding (UdpForwarder):** The packet-triggered forwarding is more realistic than independent OnOff traffic generation at CHs. This was a good design decision.
- **Priority queue with emergency detection:** The PriorityPacket struct with operator< overloading and the gateway's ProcessQueue() is a clean, correct implementation.
- **Comprehensive experiment set:** Six experiments covering scalability, traffic load, mobility, energy, and priority — this is more thorough than many published papers.
- **Reproducibility:** Same seed (42), same AODV parameters, same WiFi configuration across both scenarios. CSV output with consistent column format enables post-analysis.
- **Good project management:** Git history shows phased development, clean commit messages, organized directory structure (src/, archive/, scripts/, experiments/).
- **Heterogeneous traffic model is realistic:** ECG at 250ms, HR at 1s, Temp at 5s reflects real MIoT sensor behavior. This is a genuine advantage over constant-rate models.

---

## 3. WEAKNESSES

- **Single random seed (Seed=42, Run=1):** This is the most critical issue. Results from a single seed cannot be generalized. Statistical significance requires minimum 10-30 runs with different seeds and reporting of mean, standard deviation, and confidence intervals.
- **Unequal traffic loads not fully acknowledged:** WSN generates ~720 kbps total (180 nodes x 4 kbps) while MQTT-SN generates ~273 kbps. This 62% reduction is MQTT-SN's inherent advantage, but it means the comparison measures "realistic IoT traffic vs constant-rate" rather than "MQTT-SN protocol vs UDP protocol."
- **Energy model too simple:** WiFi 802.11b idle power (~0.82W) dominates all energy consumption, making ECG and Temperature sensors consume nearly identical energy. This is a known limitation of WiFi-based simulations — real MIoT uses BLE/802.15.4 where transmission energy matters.
- **100 seconds is short:** For 200-node networks with staggered start (5-20s), the effective measurement window is only ~80 seconds. AODV route convergence may not be complete. 300-600 seconds would be more appropriate.
- **No confidence intervals or error bars** on any results. Without these, the exact numbers (e.g., 99.97% vs 96.36%) may be artifacts of the specific random seed.
- **Priority queue processes instantly:** The gateway's ProcessQueue() empties the entire queue synchronously when any packet arrives. In reality, processing has latency. The priority queue effect is therefore not accurately reflected in the FlowMonitor delay measurements.
- **MQTT-SN protocol is simplified:** No REGISTER/REGACK for topic registration, no Will messages, no sleep state, no QoS 2 exactly-once delivery mechanism. The implementation is closer to "topic-tagged UDP" than full MQTT-SN.
- **WSN at 100 nodes anomaly:** WSN achieves 99.89% PDR at 100 nodes but drops to 96.63% at 150 — this non-monotonic behavior needs explanation. Could be related to CH grid layout changes.

---

## 4. METHODOLOGY ISSUES (DETAILED)

### 4.1 Fairness of Comparison

The comparison is **partially fair**. The infrastructure (WiFi, AODV, area, seed) is identical, which is correct. However:

**Traffic volume asymmetry:** The total traffic generated differs significantly:
- WSN: 180 x 4 kbps = 720 kbps constant
- MQTT-SN: ~60 x 4kbps (ECG) + 60 x 0.5kbps (HR) + 60 x 0.05kbps (Temp) ≈ 273 kbps

This is **intentionally different** — it reflects real sensor behavior — but the report should clearly state: "The performance improvement of MQTT-SN is partly due to its inherent traffic reduction through heterogeneous data rates." A fair same-load comparison would use OnOff with matched aggregate traffic rates.

**Recommendation:** Add one experiment where WSN also uses heterogeneous rates (4kbps for 1/3 nodes, 0.5kbps for 1/3, 0.05kbps for 1/3) to isolate the protocol overhead difference from the traffic model difference.

### 4.2 Statistical Significance

**Critical issue.** Running Seed=42, Run=1 produces ONE data point per experiment. The specific random placement of 200 nodes can significantly affect results — a different seed might produce very different cluster sizes and PDR values.

**Recommendation:** Run each experiment with at least 10 seeds (SetRun(1) through SetRun(10)) and report:
- Mean ± standard deviation
- 95% confidence intervals
- Box plots instead of single-value bar charts

This is the **number one priority** for publication readiness.

### 4.3 Simulation Duration

100 seconds with 5-20s stagger means:
- Nodes start at 5-20s (random)
- AODV route discovery takes additional 2-10s
- Effective data collection: ~70-90 seconds for most nodes
- Some late-starting nodes have only ~75s of data

For steady-state analysis, the recommended approach is:
- Warm-up period: 0-30s (discard)
- Measurement period: 30-300s

**Recommendation:** Increase to 300s minimum, with first 30s as warm-up.

### 4.4 Cluster Head Grid Calculation

The grid calculation differs slightly between files:
- WSN: `sqrt(nCH)`
- MQTT-SN: `sqrt(nCH * AREA / AREA)` = `sqrt(nCH)`

Mathematically identical, but the MQTT-SN version has a redundant `AREA/AREA` multiplication. Both produce the same grid. Not a bug, just inconsistency.

### 4.5 AODV Tuning Validity

The AODV parameter tuning (HelloInterval=2s, RreqRetries=5) is reasonable for 200 static nodes but may be suboptimal for mobility experiments. With nodes moving at 3 m/s, a 2s HelloInterval means a node can move 6 meters between Hello messages. For the 300m transmission range, this is acceptable, but at higher speeds the tuning would need revision.

---

## 5. RESULTS DISCUSSION (DETAILED)

### 5.1 The 100-Node Anomaly

In Experiment 1, WSN achieves 99.89% PDR at 100 nodes — higher than at 50 (70.22%) or 150 (96.63%). This needs explanation:

**Possible causes:**
- At 50 nodes with 5 CHs: some clusters are very unbalanced (min=7, max=16), causing congestion at overloaded CHs
- At 100 nodes with 10 CHs: better cluster balance, more CHs mean shorter hop distances
- At 150+ nodes: congestion increases despite more CHs

This non-monotonic behavior should be discussed as a **cluster balance effect** rather than ignored.

### 5.2 Broker Bottleneck Analysis

The convergence of WSN and MQTT-SN PDR at 200 nodes with broker (~70% for both) is a **strong finding**. It demonstrates that the single-sink bottleneck dominates protocol-level differences. This is the most academically interesting result because it motivates multi-sink architectures.

However, the WSN broker forwarding (UdpForwarder) creates `new Packet(size)` rather than forwarding the original packet bytes. This means FlowMonitor sees the forwarded packets as new flows, potentially inflating the flow count and affecting per-flow PDR calculations. The overall byte counts should be correct, but per-flow metrics may be misleading.

### 5.3 Energy Uniformity Problem

The ~72% uniform consumption across all sensor types is **expected but uninformative** for WiFi:

```
WiFi idle power: 0.82W x 100s = 82J consumed just for being on
Sensor TX power: 1.14W x (small duty cycle) = negligible difference
```

The battery (2.0J for sensors) depletes primarily from idle listening, not from data transmission. This is a well-known limitation of WiFi for IoT simulation. The energy experiment is **valid but of limited value** for MIoT conclusions.

**Recommendation:** Add a paragraph stating this limitation and suggesting that 802.15.4 or BLE PHY would show meaningful energy differences between sensor types.

### 5.4 Mobility Results

The PDR degradation from 71.5% to 56.3% at 3 m/s is realistic and consistent with published AODV mobility studies. The 14x increase in dead flows (211 to 2,983) is a strong quantitative result. However:

- All mobility experiments use broker=true, which adds bottleneck effects. A broker-free mobility experiment would isolate the AODV mobility impact.
- The cluster assignment is done once at simulation start. With mobility, nodes move to different CH coverage areas but remain assigned to their original CH. This means routing paths lengthen over time.

**Recommendation:** Add a note that static cluster assignment with mobile nodes is a limitation, and dynamic re-clustering would improve mobile performance.

---

## 6. CODE SUGGESTIONS

### 6.1 MqttSnHeader
- **Good:** Proper ns-3 Header subclass with Serialize/Deserialize
- **Issue:** The header is 10 bytes, while real MQTT-SN PUBLISH is 7 bytes minimum. The extra "Emergency" byte is non-standard.
- **Suggestion:** Document this as a protocol extension for MIoT, not standard MQTT-SN.

### 6.2 MqttSnGateway Priority Queue
- **Good:** Clean operator< for PriorityPacket, std::priority_queue usage
- **Issue:** ProcessQueue() is called synchronously inside HandleRead(). All queued packets are processed instantly. There is no simulated processing delay.
- **Suggestion:** Add a configurable processing delay (e.g., 1ms per packet) using Simulator::Schedule to make the priority queue effect measurable in delay statistics.

### 6.3 UdpForwarder
- **Good:** Real packet-triggered forwarding (not independent traffic)
- **Issue:** Creates new Packet instead of forwarding original bytes. The packet content (payload) is lost — only size is preserved.
- **Suggestion:** Use `packet->Copy()` instead of `Create<Packet>(packet->GetSize())` for true byte-level forwarding.

### 6.4 Emergency Detection
- **Good:** Simple, functional implementation
- **Issue:** Random probability (0.5%) is not correlated with sensor data. Real emergency detection would use threshold-based anomaly detection.
- **Suggestion:** Acceptable for simulation purposes, but document as simplified model.

### 6.5 General Code Quality
- Code is well-organized, readable, and follows ns-3 conventions
- Proper use of NS_LOG_COMPONENT, NS_OBJECT_ENSURE_REGISTERED
- CommandLine parameters are well-structured
- CSV output format is consistent and analysis-friendly

---

## 7. PUBLICATION READINESS

### For M.Sc. Thesis: READY (with minor revisions)
- Add multiple seed runs (at least 5-10)
- Explain the 100-node anomaly
- Acknowledge traffic load asymmetry explicitly
- Add energy model limitations discussion

### For Conference Paper (e.g., IEEE ICC, GLOBECOM workshops): CONDITIONALLY READY
- Must add confidence intervals from multiple runs
- Strengthen related work section
- Reduce to 3-4 key experiments with deeper analysis
- Suggested title: "Performance Comparison of Publish-Subscribe and Traditional Data Collection in Cluster-Based MIoT Networks Using ns-3"

### For Journal Paper (e.g., IEEE IoT Journal, Elsevier Ad Hoc Networks): NOT YET READY
- Needs multiple seeds + statistical analysis
- Needs comparison with at least one more routing protocol (OLSR or DSDV)
- Needs 802.15.4 PHY for meaningful energy comparison
- Needs deeper MQTT-SN implementation (QoS 2, sleep states)
- Needs comparison with existing literature benchmarks

---

## 8. RECOMMENDED ACTIONS (Prioritized)

### Priority 1 — CRITICAL (Do before thesis submission)
1. **Run experiments with 10 different seeds.** Change `SeedManager::SetRun(1)` to loop through 1-10. Report mean ± std. This alone transforms the work from "demonstration" to "study."
2. **Increase simulation time to 300 seconds** with 30s warm-up period.
3. **Explicitly acknowledge traffic asymmetry** in the report — frame it as "MQTT-SN's inherent efficiency through heterogeneous data rates."

### Priority 2 — IMPORTANT (Strengthens thesis significantly)
4. **Add same-load WSN experiment:** Configure WSN OnOff with heterogeneous rates matching MQTT-SN traffic to isolate protocol overhead from traffic model effects.
5. **Explain the 100-node WSN anomaly** — analyze cluster sizes at each node count.
6. **Add processing delay to gateway** to make priority queue effect visible in delay metrics.
7. **Run mobility experiments without broker** to isolate AODV mobility impact.

### Priority 3 — NICE TO HAVE (For publication)
8. **Add 802.15.4 PHY option** for meaningful energy comparison.
9. **Compare with OLSR routing** to show AODV-specific effects.
10. **Implement QoS 2 retransmission** in MQTT-SN for realistic exactly-once delivery.
11. **Use packet->Copy() in UdpForwarder** for byte-accurate forwarding.

### Priority 4 — FUTURE WORK (Clearly mark in thesis)
12. Dynamic re-clustering for mobile scenarios
13. Multi-sink architecture to address bottleneck
14. ML-based emergency detection
15. Security analysis (replay attack, spoofing)

---

## OVERALL ASSESSMENT

**Grade: B+ / Very Good**

This is above-average M.Sc. thesis work. The student demonstrates strong technical skills (C++, ns-3, Python analysis), good experimental design (dual comparison approach), and thorough documentation. The main gaps are in statistical rigor (single seed) and the simplified MQTT-SN implementation. With Priority 1 actions completed, this work is thesis-ready. With Priority 2 actions, it becomes conference-publishable.

The strongest aspect is the systematic comparison methodology. The weakest aspect is the lack of statistical significance from single-seed experiments.

**Recommendation: Accept with minor revisions for thesis. Revise and extend for conference submission.**
