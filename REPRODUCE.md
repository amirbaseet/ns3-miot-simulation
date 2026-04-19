# REPRODUCE.md — Full reproduction recipe (270 runs + all figures)

Reproduces every result in *Baseet & Bütün, "Performance Evaluation of
Cluster-Based WSN-AODV and MQTT-SN Architectures for Medical IoT Using
ns-3," SAUCIS 2026.*

| Item                | Value                                                |
|---------------------|------------------------------------------------------|
| Target host         | Ubuntu 22.04 LTS or Kali Linux, ≥ 8 GB RAM, ≥ 4 cores, ≥ 20 GB free disk |
| Simulator           | **ns-3 v3.40 only** — v3.41 causes PDR = 0 % in ad-hoc UDP mode |
| Wall time (Sets 1–3b) | ≈ 8 h on a 4-core machine                          |
| Wall time (Set 5)   | ≈ 2 h                                                |
| Wall time (analysis)| ≈ 10 minutes                                         |

---

## 0. System packages

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build python3 python3-pip \
                    git g++ gsl-bin libgsl-dev libgsl27 libxml2 libxml2-dev \
                    libboost-all-dev
```

## 1. Install ns-3 v3.40 (the only supported version)

```bash
cd ~
git clone https://gitlab.com/nsnam/ns-3-dev.git
cd ns-3-dev
git checkout ns-3.40
git describe --tags --exact-match        # must print: ns-3.40
./ns3 configure --enable-examples --enable-tests
./ns3 build
```

> **Do NOT use `main` / HEAD / v3.41 / v3.42 / v3.43.**
> v3.41 contains a regression that silently produces PDR = 0 % in ad-hoc UDP mode.
> All 270 CSVs in this repository were generated with **ns-3.40**.

## 2. Clone this repository and install the simulation scratch targets

```bash
cd ~
git clone https://github.com/amirbaseet/ns3-miot-simulation.git
cd ns3-miot-simulation
python3 -m pip install -r requirements.txt

mkdir -p ~/ns-3-dev/scratch/cluster-aodv-mqtt
mkdir -p ~/ns-3-dev/scratch/cluster-aodv-nosink
cp src/mqtt-sn/*                    ~/ns-3-dev/scratch/cluster-aodv-mqtt/
cp src/wsn/cluster-aodv-nosink.cc   ~/ns-3-dev/scratch/cluster-aodv-nosink/

cd ~/ns-3-dev
./ns3 build
```

## 3. Smoke-test a single 60-second run

```bash
cd ~/ns-3-dev
./ns3 run "cluster-aodv-nosink --numRegular=50 --numCH=5 --useSink=true --run=1 --simTime=60"
# Expect PDR in the 70–90 % range printed to stdout.
# If you see PDR = 0 %, re-check you are on git tag ns-3.40.
```

## 4. Run all 270 experiments

```bash
cd ~/ns-3-dev
mkdir -p experiments/statistical experiments/hier

# Sets 1, 2, 3, 3b — 240 runs, ≈ 8 h
tmux new -s experiments
bash ~/ns3-miot-simulation/scripts/run-comparison.sh
# Detach: Ctrl-B D       Reattach: tmux attach -t experiments

# Set 5 — multi-broker hierarchy, 30 runs (LB=2,4,5 × 10 seeds).
# LB=1 is NOT re-simulated; the analysis script reuses Set 2 200-node
# MQTT-SN data as the LB=1 baseline (disclosed in paper §5.7).
tmux new -s set5
bash ~/ns3-miot-simulation/scripts/run-comparison.sh --set5-only
```

## 5. Verify CSV counts

```bash
cd ~/ns-3-dev
ls experiments/statistical/exp1_*.csv       | grep -v energy | wc -l   # → 80
ls experiments/statistical/exp2_*.csv       | grep -v energy | wc -l   # → 80
ls experiments/statistical/exp3_wsn_hetero_*.csv \
                                            | grep -v energy \
                                            | grep -v broker | wc -l   # → 40
ls experiments/statistical/exp3b_*.csv      | grep -v energy | wc -l   # → 40
ls experiments/hier/exp_hier_lb*.csv        | grep -v energy | wc -l   # → 30
# Total data CSVs: 270
```

## 6. Generate every figure and statistic

```bash
cd ~/ns-3-dev
python3 ~/ns3-miot-simulation/scripts/analyze_comparison.py \
    | tee experiments/statistical/full_analysis_output.txt
```

Outputs:

- `graphs/comparison/*_en.png` and `*_tr.png` — 24 figures for Sets 1, 2, 3, 3b
- `graphs/hier/*_en.png` and `*_tr.png` — 4 figures for Set 5
- `experiments/statistical/full_analysis_output.txt` — full per-cell mean ± std
  and Welch's t-test p-values. Must match paper Tables 3 & 4.

## 7. Spot-check against the paper

```bash
# Set 2, 200-node WSN, all 10 seeds — paper Table 3: 67.4 ± 8.3 %
for r in 1 2 3 4 5 6 7 8 9 10; do
  awk -F',' 'NR>1{tx+=$4;rx+=$5} END{if(tx>0) printf "%.2f\n", 100*rx/tx}' \
      experiments/statistical/exp2_wsn_200_r${r}.csv
done | awk '{s+=$1; ss+=$1*$1; n++} END{m=s/n; printf "mean=%.2f%%  std=%.2f%%  N=%d\n", m, sqrt(ss/n - m*m), n}'
# Expected: mean ≈ 67.35 %  std ≈ 7.88 %  N=10
```

Any single seed should fall within about ±1 σ of the mean (so 59–75 %
is normal variance; anything ≤ 5 % indicates you are on ns-3.41).

---

## Troubleshooting

**All my PDRs are 0 %.**
You are on ns-3.41 or later. `git checkout ns-3.40` in `~/ns-3-dev` and
rebuild (`./ns3 build`).

**`./ns3 run` says the scratch target is missing.**
Re-run section 2 — the scratch copy step has to happen *before* the
ns-3 build.

**`scipy.stats.ttest_ind` fails in the analysis script.**
Ensure `pip install -r requirements.txt` completed. The code uses
`equal_var=False` (Welch's); this requires scipy ≥ 0.11 — trivially
satisfied by any modern install.

**I want to run only one set.**
Each set is a self-contained block in `scripts/run-comparison.sh`;
you can comment the others out or copy just the block you need.
