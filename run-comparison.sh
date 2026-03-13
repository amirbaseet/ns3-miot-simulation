#!/bin/bash
# ============================================================
# WSN vs MQTT-SN Fair Comparison
# Experiment Set 1: No Broker (Application Layer Only)
# Experiment Set 2: With Broker (Full Architecture)
# 16 total simulations
# ============================================================

cd ~/ns-3-dev
mkdir -p experiments/comparison

echo ""
echo "============================================================"
echo "  WSN vs MQTT-SN Fair Comparison"
echo "  16 simulations (2 sets x 2 scenarios x 4 node counts)"
echo "============================================================"

# ============================================================
# EXPERIMENT SET 1: NO BROKER
# ============================================================
echo ""
echo "======== SET 1: NO BROKER (Application Layer) ========"

for N in 50 100 150 200; do
    CH=$((N / 10))
    
    echo ""
    echo "[Set1-WSN] $N nodes, $CH CHs, no sink..."
    ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=false --csv=experiments/comparison/exp1_wsn_${N}.csv"
    
    echo "[Set1-MQTT] $N sensors, $CH CHs, no broker..."
    ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --broker=false --anim=false --csv=experiments/comparison/exp1_mqtt_${N}.csv"
done

# ============================================================
# EXPERIMENT SET 2: WITH BROKER
# ============================================================
echo ""
echo "======== SET 2: WITH BROKER (Full Architecture) ========"

for N in 50 100 150 200; do
    CH=$((N / 10))
    
    echo ""
    echo "[Set2-WSN] $N nodes, $CH CHs, with sink..."
    ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=true --csv=experiments/comparison/exp2_wsn_${N}.csv"
    
    echo "[Set2-MQTT] $N sensors, $CH CHs, with broker..."
    ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --broker=true --anim=false --csv=experiments/comparison/exp2_mqtt_${N}.csv"
done

echo ""
echo "============================================================"
echo "  All 16 experiments complete!"
echo "============================================================"
ls -la experiments/comparison/
