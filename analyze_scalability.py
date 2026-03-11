#!/usr/bin/env python3
"""
Scalability Analysis: WSN vs MQTT-SN
=====================================
Compares Scenario A (WSN) vs Scenario B (MQTT-SN)
across 50, 100, 150, 200 nodes.

Usage: python3 analyze_scalability.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys

matplotlib.use('Agg')

OUTPUT_DIR = "graphs/scalability"
DPI = 200

NODES = [50, 100, 150, 200]

C_WSN = '#E74C3C'   # Red
C_MQTT = '#2E86C1'  # Blue

def load_experiments():
    wsn = {}
    mqtt = {}
    
    for n in NODES:
        wf = f'experiments/wsn_{n}.csv'
        mf = f'experiments/mqtt_{n}.csv'
        
        if os.path.exists(wf):
            wsn[n] = pd.read_csv(wf)
            print(f"[OK] WSN  {n} nodes: {len(wsn[n])} flows")
        else:
            print(f"[SKIP] {wf}")
            
        if os.path.exists(mf):
            mqtt[n] = pd.read_csv(mf)
            print(f"[OK] MQTT {n} nodes: {len(mqtt[n])} flows")
        else:
            print(f"[SKIP] {mf}")
    
    return wsn, mqtt

def calc_metric(df, metric):
    if metric == 'PDR':
        tx = df['TxPackets'].sum()
        rx = df['RxPackets'].sum()
        return rx/tx*100 if tx > 0 else 0
    elif metric == 'Delay':
        d = df['AvgDelay_ms'][df['AvgDelay_ms'] > 0]
        return d.mean() if len(d) > 0 else 0
    elif metric == 'Throughput':
        return df['Throughput_kbps'].mean()
    elif metric == 'DeadFlows':
        return len(df[df['RxPackets'] == 0])
    elif metric == 'Jitter':
        j = df['AvgJitter_ms'][df['AvgJitter_ms'] > 0]
        return j.mean() if len(j) > 0 else 0
    elif metric == 'Loss':
        tx = df['TxPackets'].sum()
        rx = df['RxPackets'].sum()
        return tx - rx

def plot_comparison(wsn, mqtt, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    
    wsn_vals = [calc_metric(wsn[n], metric) if n in wsn else 0 for n in NODES]
    mqtt_vals = [calc_metric(mqtt[n], metric) if n in mqtt else 0 for n in NODES]
    
    x = np.arange(len(NODES))
    w = 0.3
    
    bars1 = ax.bar(x - w/2, wsn_vals, w, label='Scenario A: WSN (AODV+UDP)', 
                   color=C_WSN, edgecolor='white', zorder=3)
    bars2 = ax.bar(x + w/2, mqtt_vals, w, label='Scenario B: MQTT-SN', 
                   color=C_MQTT, edgecolor='white', zorder=3)
    
    # Value labels
    for b, v in zip(bars1, wsn_vals):
        fmt = f'{v:.1f}%' if 'PDR' in metric else f'{v:.1f}' if metric in ['Delay','Throughput','Jitter'] else str(int(v))
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(max(wsn_vals),max(mqtt_vals))*0.02,
                fmt, ha='center', fontsize=8, color=C_WSN, fontweight='bold')
    for b, v in zip(bars2, mqtt_vals):
        fmt = f'{v:.1f}%' if 'PDR' in metric else f'{v:.1f}' if metric in ['Delay','Throughput','Jitter'] else str(int(v))
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(max(wsn_vals),max(mqtt_vals))*0.02,
                fmt, ha='center', fontsize=8, color=C_MQTT, fontweight='bold')
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'{n} nodes' for n in NODES])
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

def plot_line(wsn, mqtt, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    
    wsn_vals = [calc_metric(wsn[n], metric) if n in wsn else 0 for n in NODES]
    mqtt_vals = [calc_metric(mqtt[n], metric) if n in mqtt else 0 for n in NODES]
    
    ax.plot(NODES, wsn_vals, 'o-', color=C_WSN, linewidth=2, markersize=8, 
            label='Scenario A: WSN (AODV+UDP)')
    ax.plot(NODES, mqtt_vals, 's-', color=C_MQTT, linewidth=2, markersize=8, 
            label='Scenario B: MQTT-SN')
    
    # Annotate values
    for i, (w, m) in enumerate(zip(wsn_vals, mqtt_vals)):
        fmt = f'{w:.1f}%' if 'PDR' in metric else f'{w:.1f}'
        ax.annotate(fmt, (NODES[i], w), textcoords="offset points", 
                    xytext=(0, 10), ha='center', fontsize=9, color=C_WSN)
        fmt = f'{m:.1f}%' if 'PDR' in metric else f'{m:.1f}'
        ax.annotate(fmt, (NODES[i], m), textcoords="offset points", 
                    xytext=(0, -15), ha='center', fontsize=9, color=C_MQTT)
    
    ax.set_xlabel('Number of Sensor Nodes', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(NODES)
    ax.legend(loc='best')
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

def plot_summary_table(wsn, mqtt):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('off')
    
    headers = ['Nodes', 'WSN PDR', 'MQTT PDR', 'WSN Delay', 'MQTT Delay', 'WSN Dead', 'MQTT Dead']
    rows = []
    for n in NODES:
        row = [f'{n}']
        if n in wsn:
            row.append(f"{calc_metric(wsn[n], 'PDR'):.2f}%")
        else:
            row.append('-')
        if n in mqtt:
            row.append(f"{calc_metric(mqtt[n], 'PDR'):.2f}%")
        else:
            row.append('-')
        if n in wsn:
            row.append(f"{calc_metric(wsn[n], 'Delay'):.2f} ms")
        else:
            row.append('-')
        if n in mqtt:
            row.append(f"{calc_metric(mqtt[n], 'Delay'):.2f} ms")
        else:
            row.append('-')
        if n in wsn:
            row.append(str(int(calc_metric(wsn[n], 'DeadFlows'))))
        else:
            row.append('-')
        if n in mqtt:
            row.append(str(int(calc_metric(mqtt[n], 'DeadFlows'))))
        else:
            row.append('-')
        rows.append(row)
    
    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    
    for j in range(len(headers)):
        table[0, j].set_facecolor('#2C3E50')
        table[0, j].set_text_props(color='white', fontweight='bold')
    
    # Color WSN columns red-ish, MQTT columns blue-ish
    for i in range(1, len(rows)+1):
        table[i, 1].set_facecolor('#FADBD8')  # WSN PDR
        table[i, 2].set_facecolor('#D6EAF8')  # MQTT PDR
        table[i, 3].set_facecolor('#FADBD8')
        table[i, 4].set_facecolor('#D6EAF8')
        table[i, 5].set_facecolor('#FADBD8')
        table[i, 6].set_facecolor('#D6EAF8')
    
    ax.set_title('WSN vs MQTT-SN: Scalability Comparison', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07_summary_table.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 07_summary_table.png")

def print_results(wsn, mqtt):
    print("\n" + "="*70)
    print("  WSN vs MQTT-SN SCALABILITY RESULTS")
    print("="*70)
    print(f"  {'Nodes':<8} {'WSN PDR':<12} {'MQTT PDR':<12} {'WSN Delay':<12} {'MQTT Delay':<12}")
    print("  " + "-"*56)
    for n in NODES:
        wp = f"{calc_metric(wsn[n], 'PDR'):.2f}%" if n in wsn else "-"
        mp = f"{calc_metric(mqtt[n], 'PDR'):.2f}%" if n in mqtt else "-"
        wd = f"{calc_metric(wsn[n], 'Delay'):.2f}ms" if n in wsn else "-"
        md = f"{calc_metric(mqtt[n], 'Delay'):.2f}ms" if n in mqtt else "-"
        print(f"  {n:<8} {wp:<12} {mp:<12} {wd:<12} {md:<12}")
    print("="*70 + "\n")

if __name__ == "__main__":
    print("\n[MIoT] WSN vs MQTT-SN Scalability Analysis\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    wsn, mqtt = load_experiments()
    
    if len(wsn) == 0 and len(mqtt) == 0:
        print("[ERROR] No experiment data found!")
        print("Run experiments first: bash run-experiments.sh")
        sys.exit(1)
    
    # Bar charts
    plot_comparison(wsn, mqtt, 'PDR', 'PDR (%)', 'PDR: WSN vs MQTT-SN', '01_pdr_bars.png')
    plot_comparison(wsn, mqtt, 'Delay', 'Avg Delay (ms)', 'Delay: WSN vs MQTT-SN', '02_delay_bars.png')
    plot_comparison(wsn, mqtt, 'Throughput', 'Throughput (kbps)', 'Throughput: WSN vs MQTT-SN', '03_throughput_bars.png')
    plot_comparison(wsn, mqtt, 'DeadFlows', 'Dead Flows', 'Dead Flows: WSN vs MQTT-SN', '04_dead_bars.png')
    
    # Line charts (scalability trend)
    plot_line(wsn, mqtt, 'PDR', 'PDR (%)', 'PDR Scalability Trend', '05_pdr_line.png')
    plot_line(wsn, mqtt, 'Delay', 'Avg Delay (ms)', 'Delay Scalability Trend', '06_delay_line.png')
    
    # Summary table
    plot_summary_table(wsn, mqtt)
    
    print_results(wsn, mqtt)
