#!/usr/bin/env bash
# ============================================================
# run-comparison.sh — drive all 270 ns-3 simulations for the SAUCIS paper.
#
# Paper:   A. Baseet and İ. Bütün, "Performance Evaluation of Cluster-Based
#          WSN-AODV and MQTT-SN Architectures for Medical IoT Using ns-3,"
#          SAUCIS, 2026 (under review).
# Repo:    https://github.com/amirbaseet/ns3-miot-simulation
#
# Usage:
#   bash scripts/run-comparison.sh                # Sets 1, 2, 3, 3b, 5  (270 runs)
#   bash scripts/run-comparison.sh --set5-only    # Set 5 only           ( 30 runs)
#
# Prerequisites:
#   * ns-3 v3.40 built under ~/ns-3-dev  (v3.41 causes PDR=0% — DO NOT USE)
#   * Scratch targets cluster-aodv-mqtt and cluster-aodv-nosink installed
#     (see README.md §Build and REPRODUCE.md)
#   * tmux strongly recommended: ≈ 8 h on a 4-core machine.
#
# Sets produced:
#   1  — No broker              (WSN vs MQTT-SN, 50/100/150/200 nodes)
#   2  — With broker            (WSN vs MQTT-SN, 50/100/150/200 nodes)
#   3  — Equal load, no broker  (WSN-Hetero vs MQTT-SN)
#   3b — Equal load, with broker
#   5  — Multi-broker hierarchy (MQTT-SN, 200 nodes, LB=2/4/5 — LB=1 is
#        reused from Set 2 and is not re-simulated here)
#
# Output:  ~/ns-3-dev/experiments/statistical/  and  ~/ns-3-dev/experiments/hier/
# ============================================================
set -uo pipefail

# --- Argument parsing ---
RUN_SETS_1_TO_3B=1
case "${1:-}" in
    --set5-only)      RUN_SETS_1_TO_3B=0 ;;
    -h|--help)        sed -n '2,30p' "$0"; exit 0 ;;
    "")               ;;   # default: run everything
    *)                echo "Unknown argument: $1"; echo "Use --help for usage."; exit 2 ;;
esac

cd ~/ns-3-dev
mkdir -p experiments/statistical experiments/hier

SIMTIME=300
SEEDS=10

echo ""
echo "============================================================"
echo "  WSN vs MQTT-SN + Multi-Broker Hierarchy"
echo "  Seeds: $SEEDS | SimTime: ${SIMTIME}s"
echo "  Mode:  $([ $RUN_SETS_1_TO_3B -eq 1 ] && echo 'full (Sets 1-3b + Set 5)' || echo 'Set 5 only')"
echo "============================================================"

if [ $RUN_SETS_1_TO_3B -eq 1 ]; then

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

fi  # end of: if [ $RUN_SETS_1_TO_3B -eq 1 ]

# ============================================================
# SET 5: MULTI-BROKER HIERARCHY SWEEP
# Fixed: 200 nodes, 20 CHs, 10 seeds
# Varies: numLocalBrokers = 2, 4, 5
# NOTE: LB=1 is NOT re-simulated here. The single-broker baseline
#       reuses Set 2 200-node MQTT-SN data (exp2_mqtt_200_r{1-10}.csv);
#       see paper §5.7 and scripts/analyze_comparison.py.
# ============================================================
echo ""
echo "======== SET 5: MULTI-BROKER HIERARCHY (200 nodes, 10 seeds) ========"
N=200
CH=20
for LB in 2 4 5; do
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
