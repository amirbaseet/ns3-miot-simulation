#!/bin/bash
# ============================================================
# WSN vs MQTT-SN Fair Comparison (Statistical Version)
# 10 seeds x 2 sets x 2 scenarios x 4 node counts
# SimTime: 300s (increased from 100s for steady-state)
# ============================================================

cd ~/ns-3-dev
mkdir -p experiments/statistical

SIMTIME=300
SEEDS=10  # Number of runs per experiment

echo ""
echo "============================================================"
echo "  WSN vs MQTT-SN Fair Comparison (Statistical)"
echo "  Seeds: $SEEDS | SimTime: ${SIMTIME}s"
echo "  Total: $((SEEDS * 2 * 2 * 4)) simulations"
echo "============================================================"

# ============================================================
# EXPERIMENT SET 1: NO BROKER
# ============================================================
echo ""
echo "======== SET 1: NO BROKER (Application Layer) ========"

for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set1-WSN] N=$N CH=$CH Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=false --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp1_wsn_${N}_r${RUN}.csv" 2>/dev/null

        echo "[Set1-MQTT] N=$N CH=$CH Run=$RUN..."
        ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --broker=false --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/statistical/exp1_mqtt_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set1 N=$N complete ($SEEDS runs each)"
done

# ============================================================
# EXPERIMENT SET 2: WITH BROKER
# ============================================================
echo ""
echo "======== SET 2: WITH BROKER (Full Architecture) ========"

for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set2-WSN] N=$N CH=$CH Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=true --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp2_wsn_${N}_r${RUN}.csv" 2>/dev/null

        echo "[Set2-MQTT] N=$N CH=$CH Run=$RUN..."
        ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --broker=true --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/statistical/exp2_mqtt_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set2 N=$N complete ($SEEDS runs each)"
done

echo ""
echo "============================================================"
echo "  All main experiments complete!"
echo "============================================================"

# ============================================================
# EXPERIMENT SET 3: SAME-LOAD WSN (Heterogeneous, 10 seeds)
# Isolates protocol overhead from traffic model difference
# ============================================================
echo ""
echo "======== SET 3: SAME-LOAD (Hetero WSN vs MQTT-SN, No Broker) ========"

for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set3-WSN-Hetero] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=false --hetero=true --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp3_wsn_hetero_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set3 N=$N complete ($SEEDS runs)"
done

# ============================================================
# EXPERIMENT SET 4: MOBILITY WITHOUT BROKER (10 seeds)
# Isolates AODV mobility impact from broker bottleneck
# ============================================================
echo ""
echo "======== SET 4: MOBILITY NO BROKER (10 seeds) ========"

for SPEED in 0 0.5 1.5 3.0; do
    SNAME=$(echo $SPEED | tr '.' '_')
    for RUN in $(seq 1 $SEEDS); do
        if [ "$SPEED" = "0" ]; then
            echo "[Set4] Static Run=$RUN..."
            ./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=false --mobility=false --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/statistical/exp4_mob_${SNAME}_r${RUN}.csv" 2>/dev/null
        else
            echo "[Set4] Speed=${SPEED}m/s Run=$RUN..."
            ./ns3 run "cluster-aodv-mqtt --nSensors=180 --nCH=20 --broker=false --mobility=true --speed=$SPEED --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/statistical/exp4_mob_${SNAME}_r${RUN}.csv" 2>/dev/null
        fi
    done
    echo "[OK] Set4 Speed=$SPEED complete ($SEEDS runs)"
done

echo ""
echo "============================================================"
echo "  ALL EXPERIMENTS COMPLETE!"
echo "============================================================"
ls experiments/statistical/*.csv 2>/dev/null | wc -l
echo "total CSV files."
