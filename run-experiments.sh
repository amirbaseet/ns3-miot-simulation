#!/bin/bash
# ============================================================
# MIoT Scalability Experiment (Fixed)
# Scenario A: WSN (AODV + UDP)
# Scenario B: MQTT-SN + Priority + Broker
# Node counts: 50, 100, 150, 200
# ============================================================

cd ~/ns-3-dev
mkdir -p experiments

echo ""
echo "============================================"
echo "  MIoT Scalability Experiment"
echo "============================================"

# ---- SCENARIO A: WSN ----
echo ""
echo "===== SCENARIO A: WSN (AODV + UDP) ====="

for N in 50 100 150 200; do
    CH=$((N / 10))
    echo ""
    echo "[A] $N nodes, $CH CHs..."
    ./ns3 run "scratch/cluster-aodv-nosink --numRegular=$N --numCH=$CH --simTime=100 --anim=false --csv=experiments/wsn_${N}.csv" 2>/dev/null
    echo "[A] OK: wsn_${N}.csv"
done

# ---- SCENARIO B: MQTT-SN ----
echo ""
echo "===== SCENARIO B: MQTT-SN + Broker ====="

for N in 50 100 150 200; do
    CH=$((N / 10))
    echo ""
    echo "[B] $N sensors, $CH CHs + broker..."
    ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --broker=true --anim=false --csv=experiments/mqtt_${N}.csv" 2>/dev/null
    echo "[B] OK: mqtt_${N}.csv"
done

echo ""
echo "============================================"
echo "  Done! Results:"
echo "============================================"
ls -la experiments/*.csv
