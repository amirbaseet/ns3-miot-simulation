#!/bin/bash
# ============================================================
# Traffic Load Experiment
# Same network (180 sensors, 20 CH) but different ECG ratios
# ECG sends every 250ms (heavy), Temp sends every 5s (light)
# ============================================================

cd ~/ns-3-dev
mkdir -p experiments

echo ""
echo "============================================"
echo "  Traffic Load Experiment"
echo "  180 sensors, 20 CH, vary ECG/HR/Temp ratio"
echo "============================================"

# Low traffic: mostly temperature (light)
echo ""
echo "[1/3] LOW traffic: 20 ECG + 20 HR + 140 Temp..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --nECG=20 --nHR=20 --broker=true --anim=false --csv=experiments/traffic_low.csv"
echo "[OK] traffic_low.csv"

# Medium traffic: balanced (current default)
echo ""
echo "[2/3] MEDIUM traffic: 60 ECG + 60 HR + 60 Temp..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --nECG=60 --nHR=60 --broker=true --anim=false --csv=experiments/traffic_medium.csv"
echo "[OK] traffic_medium.csv"

# High traffic: mostly ECG (heavy)
echo ""
echo "[3/3] HIGH traffic: 140 ECG + 20 HR + 20 Temp..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --nECG=140 --nHR=20 --broker=true --anim=false --csv=experiments/traffic_high.csv"
echo "[OK] traffic_high.csv"

echo ""
echo "============================================"
echo "  Done! Results:"
echo "============================================"
ls -la experiments/traffic_*.csv
