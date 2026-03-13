#!/usr/bin/env python3
"""
WSN vs MQTT-SN Fair Comparison Analysis
=========================================
Set 1: No Broker (Application Layer)
Set 2: With Broker (Full Architecture)
Each set: WSN vs MQTT-SN at 50/100/150/200 nodes

Usage: python3 analyze_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys

matplotlib.use('Agg')

OUTPUT_DIR = "graphs/comparison"
DPI = 200
NODES = [50, 100, 150, 200]

# Colors
C_WSN = '#E74C3C'
C_MQTT = '#2E86C1'
C_WSN_L = '#F5B7B1'
C_MQTT_L = '#AED6F1'

def load_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

def calc(df):
    if df is None: return {'PDR': 0, 'Delay': 0, 'Throughput': 0, 'Dead': 0, 'Tx': 0, 'Rx': 0}
    tx = df['TxPackets'].sum()
    rx = df['RxPackets'].sum()
    d = df['AvgDelay_ms'][df['AvgDelay_ms'] > 0]
    return {
        'PDR': rx/tx*100 if tx > 0 else 0,
        'Delay': d.mean() if len(d) > 0 else 0,
        'Throughput': df['Throughput_kbps'].mean(),
        'Dead': len(df[df['RxPackets'] == 0]),
        'Tx': tx, 'Rx': rx
    }

def load_all():
    data = {}
    for s in [1, 2]:
        for t in ['wsn', 'mqtt']:
            for n in NODES:
                key = f"exp{s}_{t}_{n}"
                path = f"experiments/comparison/{key}.csv"
                df = load_csv(path)
                if df is not None:
                    data[key] = calc(df)
                    print(f"[OK] {key}: {len(df)} flows")
                else:
                    print(f"[SKIP] {path}")
    return data

# ============================================================
# SET-SPECIFIC PLOTS (Bar charts for each set)
# ============================================================
def plot_set_bars(data, setnum, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    prefix = f"exp{setnum}"
    
    wsn_vals = [data.get(f"{prefix}_wsn_{n}", {}).get(metric, 0) for n in NODES]
    mqtt_vals = [data.get(f"{prefix}_mqtt_{n}", {}).get(metric, 0) for n in NODES]
    
    x = np.arange(len(NODES))
    w = 0.3
    
    bars1 = ax.bar(x - w/2, wsn_vals, w, label='WSN (AODV+UDP)', color=C_WSN, edgecolor='white', zorder=3)
    bars2 = ax.bar(x + w/2, mqtt_vals, w, label='MQTT-SN', color=C_MQTT, edgecolor='white', zorder=3)
    
    maxv = max(max(wsn_vals), max(mqtt_vals)) if wsn_vals and mqtt_vals else 1
    for b, v in zip(bars1, wsn_vals):
        fmt = f'{v:.1f}%' if 'PDR' in metric else f'{v:.1f}ms' if 'Delay' in metric else f'{v:.0f}' 
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+maxv*0.02, fmt, ha='center', fontsize=8, fontweight='bold', color=C_WSN)
    for b, v in zip(bars2, mqtt_vals):
        fmt = f'{v:.1f}%' if 'PDR' in metric else f'{v:.1f}ms' if 'Delay' in metric else f'{v:.0f}'
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+maxv*0.02, fmt, ha='center', fontsize=8, fontweight='bold', color=C_MQTT)
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'{n} nodes' for n in NODES])
    ax.set_ylabel(ylabel, fontsize=12)
    setname = "No Broker" if setnum == 1 else "With Broker"
    ax.set_title(f'{title} — {setname}', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

# ============================================================
# LINE CHARTS (Scalability trends)
# ============================================================
def plot_set_lines(data, setnum, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    prefix = f"exp{setnum}"
    
    wsn_vals = [data.get(f"{prefix}_wsn_{n}", {}).get(metric, 0) for n in NODES]
    mqtt_vals = [data.get(f"{prefix}_mqtt_{n}", {}).get(metric, 0) for n in NODES]
    
    ax.plot(NODES, wsn_vals, 'o-', color=C_WSN, linewidth=2, markersize=8, label='WSN (AODV+UDP)')
    ax.plot(NODES, mqtt_vals, 's-', color=C_MQTT, linewidth=2, markersize=8, label='MQTT-SN')
    
    for i, (w, m) in enumerate(zip(wsn_vals, mqtt_vals)):
        fmt = f'{w:.1f}%' if 'PDR' in metric else f'{w:.1f}'
        ax.annotate(fmt, (NODES[i], w), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9, color=C_WSN)
        fmt = f'{m:.1f}%' if 'PDR' in metric else f'{m:.1f}'
        ax.annotate(fmt, (NODES[i], m), textcoords="offset points", xytext=(0, -15), ha='center', fontsize=9, color=C_MQTT)
    
    ax.set_xlabel('Number of Sensor Nodes', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    setname = "No Broker" if setnum == 1 else "With Broker"
    ax.set_title(f'{title} — {setname}', fontsize=14, fontweight='bold')
    ax.set_xticks(NODES)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

# ============================================================
# BROKER IMPACT (Set 1 vs Set 2)
# ============================================================
def plot_broker_impact(data):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Broker/Sink Impact on PDR', fontsize=16, fontweight='bold')
    
    # WSN: broker impact
    ax = axes[0]
    wsn_no = [data.get(f"exp1_wsn_{n}", {}).get('PDR', 0) for n in NODES]
    wsn_yes = [data.get(f"exp2_wsn_{n}", {}).get('PDR', 0) for n in NODES]
    ax.plot(NODES, wsn_no, 'o-', color=C_WSN, linewidth=2, markersize=8, label='WSN No Sink')
    ax.plot(NODES, wsn_yes, 's--', color=C_WSN_L, linewidth=2, markersize=8, label='WSN With Sink')
    for i in range(len(NODES)):
        ax.annotate(f'{wsn_no[i]:.1f}%', (NODES[i], wsn_no[i]), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
        ax.annotate(f'{wsn_yes[i]:.1f}%', (NODES[i], wsn_yes[i]), textcoords="offset points", xytext=(0, -15), ha='center', fontsize=9)
    ax.set_xlabel('Nodes'); ax.set_ylabel('PDR (%)')
    ax.set_title('WSN: Broker Impact', fontweight='bold')
    ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
    
    # MQTT-SN: broker impact
    ax = axes[1]
    mqtt_no = [data.get(f"exp1_mqtt_{n}", {}).get('PDR', 0) for n in NODES]
    mqtt_yes = [data.get(f"exp2_mqtt_{n}", {}).get('PDR', 0) for n in NODES]
    ax.plot(NODES, mqtt_no, 'o-', color=C_MQTT, linewidth=2, markersize=8, label='MQTT-SN No Broker')
    ax.plot(NODES, mqtt_yes, 's--', color=C_MQTT_L, linewidth=2, markersize=8, label='MQTT-SN With Broker')
    for i in range(len(NODES)):
        ax.annotate(f'{mqtt_no[i]:.1f}%', (NODES[i], mqtt_no[i]), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
        ax.annotate(f'{mqtt_yes[i]:.1f}%', (NODES[i], mqtt_yes[i]), textcoords="offset points", xytext=(0, -15), ha='center', fontsize=9)
    ax.set_xlabel('Nodes'); ax.set_ylabel('PDR (%)')
    ax.set_title('MQTT-SN: Broker Impact', fontweight='bold')
    ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '09_broker_impact.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 09_broker_impact.png")

# ============================================================
# MASTER DASHBOARD (All 4 scenarios)
# ============================================================
def plot_master_dashboard(data):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('WSN vs MQTT-SN — Complete Comparison Dashboard', fontsize=18, fontweight='bold')
    
    scenarios = [
        ('exp1_wsn', 'WSN No Sink', C_WSN, 'o-'),
        ('exp1_mqtt', 'MQTT-SN No Broker', C_MQTT, 's-'),
        ('exp2_wsn', 'WSN With Sink', C_WSN_L, 'o--'),
        ('exp2_mqtt', 'MQTT-SN With Broker', C_MQTT_L, 's--'),
    ]
    
    for ax, metric, ylabel, title in [
        (axes[0,0], 'PDR', 'PDR (%)', 'Packet Delivery Ratio'),
        (axes[0,1], 'Delay', 'Avg Delay (ms)', 'End-to-End Delay'),
        (axes[1,0], 'Throughput', 'Throughput (kbps)', 'Throughput'),
        (axes[1,1], 'Dead', 'Dead Flows', 'Dead Flows')]:
        
        for prefix, label, color, style in scenarios:
            vals = [data.get(f"{prefix}_{n}", {}).get(metric, 0) for n in NODES]
            ax.plot(NODES, vals, style, color=color, linewidth=2, markersize=6, label=label)
        
        ax.set_xlabel('Nodes')
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontweight='bold')
        ax.set_xticks(NODES)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '10_master_dashboard.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 10_master_dashboard.png")

# ============================================================
# SUMMARY TABLE
# ============================================================
def plot_summary_table(data):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('off')
    
    headers = ['Set', 'Nodes', 'WSN PDR', 'MQTT PDR', 'WSN Delay', 'MQTT Delay', 'WSN Dead', 'MQTT Dead', 'Winner']
    rows = []
    
    for s in [1, 2]:
        setname = "No Broker" if s == 1 else "With Broker"
        for n in NODES:
            wsn = data.get(f"exp{s}_wsn_{n}", {})
            mqtt = data.get(f"exp{s}_mqtt_{n}", {})
            
            wpdr = wsn.get('PDR', 0)
            mpdr = mqtt.get('PDR', 0)
            winner = "MQTT-SN" if mpdr > wpdr + 1 else "WSN" if wpdr > mpdr + 1 else "Tie"
            
            rows.append([
                setname, str(n),
                f"{wpdr:.2f}%", f"{mpdr:.2f}%",
                f"{wsn.get('Delay',0):.2f}ms", f"{mqtt.get('Delay',0):.2f}ms",
                str(int(wsn.get('Dead',0))), str(int(mqtt.get('Dead',0))),
                winner
            ])
    
    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    
    for j in range(len(headers)):
        table[0, j].set_facecolor('#2C3E50')
        table[0, j].set_text_props(color='white', fontweight='bold')
    
    for i in range(1, len(rows)+1):
        winner = rows[i-1][-1]
        if winner == "MQTT-SN":
            for j in range(len(headers)):
                table[i, j].set_facecolor('#D6EAF8')
        elif winner == "WSN":
            for j in range(len(headers)):
                table[i, j].set_facecolor('#FADBD8')
    
    ax.set_title('WSN vs MQTT-SN: Complete Results Summary\n(Blue=MQTT-SN wins, Red=WSN wins)', 
                  fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11_summary_table.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 11_summary_table.png")

# ============================================================
def print_results(data):
    print("\n" + "="*90)
    print("  WSN vs MQTT-SN FAIR COMPARISON — COMPLETE RESULTS")
    print("="*90)
    
    for s in [1, 2]:
        setname = "NO BROKER" if s == 1 else "WITH BROKER"
        print(f"\n  --- SET {s}: {setname} ---")
        print(f"  {'Nodes':<8} {'WSN PDR':<12} {'MQTT PDR':<12} {'WSN Delay':<12} {'MQTT Delay':<12} {'Winner':<10}")
        print("  " + "-"*66)
        for n in NODES:
            wsn = data.get(f"exp{s}_wsn_{n}", {})
            mqtt = data.get(f"exp{s}_mqtt_{n}", {})
            wpdr = wsn.get('PDR', 0)
            mpdr = mqtt.get('PDR', 0)
            winner = "MQTT-SN" if mpdr > wpdr + 1 else "WSN" if wpdr > mpdr + 1 else "~Tie"
            print(f"  {n:<8} {wpdr:.2f}%{'':<5} {mpdr:.2f}%{'':<5} {wsn.get('Delay',0):.2f}ms{'':<5} {mqtt.get('Delay',0):.2f}ms{'':<5} {winner}")
    
    print("\n" + "="*90)
    print(f"  Graphs saved in: {OUTPUT_DIR}/")
    print("="*90 + "\n")

# ============================================================
if __name__ == "__main__":
    print("\n[MIoT] WSN vs MQTT-SN Fair Comparison Analysis\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    
    if len(data) == 0:
        print("[ERROR] No data found!"); sys.exit(1)
    
    # Set 1: No Broker
    plot_set_bars(data, 1, 'PDR', 'PDR (%)', 'PDR: WSN vs MQTT-SN', '01_set1_pdr_bars.png')
    plot_set_bars(data, 1, 'Delay', 'Delay (ms)', 'Delay: WSN vs MQTT-SN', '02_set1_delay_bars.png')
    plot_set_bars(data, 1, 'Dead', 'Dead Flows', 'Dead Flows: WSN vs MQTT-SN', '03_set1_dead_bars.png')
    plot_set_lines(data, 1, 'PDR', 'PDR (%)', 'PDR Scalability', '04_set1_pdr_line.png')
    
    # Set 2: With Broker
    plot_set_bars(data, 2, 'PDR', 'PDR (%)', 'PDR: WSN vs MQTT-SN', '05_set2_pdr_bars.png')
    plot_set_bars(data, 2, 'Delay', 'Delay (ms)', 'Delay: WSN vs MQTT-SN', '06_set2_delay_bars.png')
    plot_set_bars(data, 2, 'Dead', 'Dead Flows', 'Dead Flows: WSN vs MQTT-SN', '07_set2_dead_bars.png')
    plot_set_lines(data, 2, 'PDR', 'PDR (%)', 'PDR Scalability', '08_set2_pdr_line.png')
    
    # Cross comparison
    plot_broker_impact(data)
    plot_master_dashboard(data)
    plot_summary_table(data)
    
    print_results(data)
