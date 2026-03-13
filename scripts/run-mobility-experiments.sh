#!/bin/bash
# ============================================================
# Mobility Experiment
# Static vs Walking vs Running patients
# 180 sensors, 20 CH, broker enabled
# ============================================================

cd ~/ns-3-dev
mkdir -p experiments

echo ""
echo "============================================"
echo "  Mobility Experiment"
echo "  180 sensors, 20 CH + broker"
echo "============================================"

# Static (baseline)
echo ""
echo "[1/4] STATIC (no mobility)..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=false --anim=false --csv=experiments/mobility_static.csv"
echo "[OK] mobility_static.csv"

# Slow walking (0.5 m/s)
echo ""
echo "[2/4] SLOW walking (0.5 m/s)..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=true --speed=0.5 --anim=false --csv=experiments/mobility_slow.csv"
echo "[OK] mobility_slow.csv"

# Normal walking (1.5 m/s)
echo ""
echo "[3/4] NORMAL walking (1.5 m/s)..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=true --speed=1.5 --anim=false --csv=experiments/mobility_normal.csv"
echo "[OK] mobility_normal.csv"

# Fast / running (3.0 m/s)
echo ""
echo "[4/4] FAST running (3.0 m/s)..."
./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=true --mobility=true --speed=3.0 --anim=false --csv=experiments/mobility_fast.csv"
echo "[OK] mobility_fast.csv"

echo ""
echo "============================================"
echo "  Done! Results:"
echo "============================================"
ls -la experiments/mobility_*.csv
