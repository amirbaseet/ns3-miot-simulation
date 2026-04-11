#!/bin/bash
# ============================================================
# WSN vs MQTT-SN Fair Comparison (Statistical Version)
# ============================================================
# Sets:
#   1  — No broker           (WSN vs MQTT-SN, 50/100/150/200 nodes)
#   2  — With broker         (WSN vs MQTT-SN, 50/100/150/200 nodes)
#   3  — Equal load, no broker  (WSN-Hetero vs MQTT-SN)
#   3b — Equal load, with broker
#   5  — Multi-broker hierarchy (MQTT-SN, 200 nodes, LB=1/2/4/5)
# ============================================================

cd ~/ns-3-dev
mkdir -p experiments/statistical experiments/hier

SIMTIME=300
SEEDS=10

echo ""
echo "============================================================"
echo "  WSN vs MQTT-SN + Multi-Broker Hierarchy"
echo "  Seeds: $SEEDS | SimTime: ${SIMTIME}s"
echo "============================================================"

# ============================================================
# SET 1: NO BROKER
# ============================================================
echo ""
echo "======== SET 1: NO BROKER ========"
for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set1-WSN] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=false --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp1_wsn_${N}_r${RUN}.csv" 2>/dev/null
        echo "[Set1-MQTT] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --numLocalBrokers=0 --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/statistical/exp1_mqtt_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set1 N=$N complete"
done

# ============================================================
# SET 2: WITH BROKER (single)
# ============================================================
echo ""
echo "======== SET 2: WITH BROKER ========"
for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set2-WSN] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=true --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp2_wsn_${N}_r${RUN}.csv" 2>/dev/null
        echo "[Set2-MQTT] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --numLocalBrokers=1 --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/statistical/exp2_mqtt_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set2 N=$N complete"
done

# ============================================================
# SET 3: EQUAL LOAD, NO BROKER
# ============================================================
echo ""
echo "======== SET 3: EQUAL LOAD, NO BROKER ========"
for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set3-WSN-Hetero] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=false --hetero=true --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp3_wsn_hetero_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set3 N=$N complete"
done

# ============================================================
# SET 3b: EQUAL LOAD, WITH BROKER
# ============================================================
echo ""
echo "======== SET 3b: EQUAL LOAD, WITH BROKER ========"
for N in 50 100 150 200; do
    CH=$((N / 10))
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set3b-WSN-Hetero] N=$N Run=$RUN..."
        ./ns3 run "cluster-aodv-nosink --numRegular=$N --numCH=$CH --useSink=true --hetero=true --run=$RUN --simTime=$SIMTIME --csv=experiments/statistical/exp3b_wsn_hetero_broker_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set3b N=$N complete"
done

# ============================================================
# SET 5: MULTI-BROKER HIERARCHY SWEEP
# Fixed: 200 nodes, 20 CHs, 10 seeds
# Varies: numLocalBrokers = 1 (baseline), 2, 4, 5
# ============================================================
echo ""
echo "======== SET 5: MULTI-BROKER HIERARCHY (200 nodes, 10 seeds) ========"
N=200
CH=20
for LB in 1 2 4 5; do
    for RUN in $(seq 1 $SEEDS); do
        echo "[Set5-Hier] LB=$LB Run=$RUN..."
        ./ns3 run "cluster-aodv-mqtt --nSensors=$N --nCH=$CH --numLocalBrokers=$LB --run=$RUN --simTime=$SIMTIME --anim=false --csv=experiments/hier/exp_hier_lb${LB}_${N}_r${RUN}.csv" 2>/dev/null
    done
    echo "[OK] Set5 LB=$LB complete ($SEEDS seeds)"
done

echo ""
echo "============================================================"
echo "  ALL EXPERIMENTS COMPLETE!"
echo "============================================================"
echo "Statistical CSVs:"
ls experiments/statistical/*.csv 2>/dev/null | wc -l
echo "Hierarchy CSVs:"
ls experiments/hier/*.csv 2>/dev/null | wc -l
echo "total CSV files."
