#!/usr/bin/env python3
"""
MIoT Simulation - 4 Phase Comparative Analysis
================================================
Phase 1: OnOff baseline
Phase 2: MQTT-SN basic
Phase 3: Priority MQTT-SN
Phase 4: Broker/Sink

Usage: python3 compare_phases.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys

matplotlib.use('Agg')

OUTPUT_DIR = "graphs"
DPI = 200

C1 = '#E74C3C'  # Phase 1 Red
C2 = '#2E86C1'  # Phase 2 Blue
C3 = '#27AE60'  # Phase 3 Green
C4 = '#F39C12'  # Phase 4 Orange

def load_all():
    files = {
        'Phase 1\n(OnOff)': 'results/cluster-aodv-nosink-results.csv',
        'Phase 2\n(MQTT-SN)': 'results/mqtt-sn-results.csv',
        'Phase 3\n(Priority)': 'results/mqtt-sn-priority-results.csv',
        'Phase 4\n(Broker)': 'results/mqtt-sn-broker-results.csv',
    }
    data = {}
    for name, path in files.items():
        if os.path.exists(path):
            data[name] = pd.read_csv(path)
            print(f"[OK] {name.replace(chr(10),' ')}: {len(data[name])} flows")
        else:
            print(f"[SKIP] {path} not found")
    if len(data) == 0:
        print("[ERROR] No CSV files found!"); sys.exit(1)
    return data

def calc_stats(data):
    stats = {}
    for name, df in data.items():
        tx = df['TxPackets'].sum()
        rx = df['RxPackets'].sum()
        stats[name] = {
            'PDR': rx/tx*100 if tx > 0 else 0,
            'AvgDelay': df['AvgDelay_ms'][df['AvgDelay_ms']>0].mean() if len(df[df['AvgDelay_ms']>0])>0 else 0,
            'Throughput': df['Throughput_kbps'].mean(),
            'DeadFlows': len(df[df['RxPackets']==0]),
            'TotalFlows': len(df),
            'TxPackets': tx, 'RxPackets': rx,
            'LostPackets': tx - rx,
            'AvgJitter': df['AvgJitter_ms'][df['AvgJitter_ms']>0].mean() if len(df[df['AvgJitter_ms']>0])>0 else 0,
        }
    return stats

def get_colors(n):
    return [C1, C2, C3, C4][:n]

def plot_bar(stats, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    names = list(stats.keys())
    values = [stats[n][metric] for n in names]
    colors = get_colors(len(names))
    bars = ax.bar(names, values, color=colors, edgecolor='white', width=0.5, zorder=3)
    for b, v in zip(bars, values):
        fmt = f'{v:.2f}%' if 'PDR' in metric else f'{v:.2f} ms' if 'Delay' in metric else f'{v:.1f}' if 'Throughput' in metric else str(int(v))
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(values)*0.03, fmt, ha='center', fontweight='bold', fontsize=11)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

def plot_boxplot(data, column, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    plot_data = []
    labels = []
    colors = get_colors(len(data))
    for name, df in data.items():
        d = df[column].dropna()
        if column != 'PDR_pct': d = d[d > 0]
        plot_data.append(d)
        labels.append(name)
    bp = ax.boxplot(plot_data, labels=labels, patch_artist=True, widths=0.4,
                    medianprops=dict(color='black', linewidth=2))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color); patch.set_alpha(0.6)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

def plot_packets(stats):
    fig, ax = plt.subplots(figsize=(9, 5))
    names = list(stats.keys())
    rx = [stats[n]['RxPackets'] for n in names]
    lost = [stats[n]['LostPackets'] for n in names]
    x = np.arange(len(names))
    ax.bar(x, rx, 0.4, label='Delivered', color=C3, edgecolor='white', zorder=3)
    ax.bar(x, lost, 0.4, bottom=rx, label='Lost', color=C1, edgecolor='white', zorder=3)
    for i, (r, l) in enumerate(zip(rx, lost)):
        total = r + l
        pct = r/total*100 if total > 0 else 0
        ax.text(i, total+max(rx)*0.02, f'{pct:.1f}%', ha='center', fontweight='bold', fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel('Packets', fontsize=12)
    ax.set_title('Delivered vs Lost Packets', fontsize=15, fontweight='bold')
    ax.legend(); ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07_packet_stats.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 07_packet_stats.png")

def plot_summary(stats):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('MIoT Simulation — 4 Phase Comparison Dashboard', fontsize=18, fontweight='bold')
    names = list(stats.keys())
    colors = get_colors(len(names))

    # PDR
    ax = axes[0,0]
    vals = [stats[n]['PDR'] for n in names]
    bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.5, f'{v:.1f}%', ha='center', fontweight='bold')
    ax.set_title('PDR (%)', fontweight='bold'); ax.set_ylim(0, 115); ax.grid(axis='y', alpha=0.3)

    # Delay
    ax = axes[0,1]
    vals = [stats[n]['AvgDelay'] for n in names]
    bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, f'{v:.1f}ms', ha='center', fontweight='bold')
    ax.set_title('Avg Delay (ms)', fontweight='bold'); ax.grid(axis='y', alpha=0.3)

    # Dead Flows
    ax = axes[1,0]
    vals = [stats[n]['DeadFlows'] for n in names]
    bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, str(v), ha='center', fontweight='bold')
    ax.set_title('Dead Flows', fontweight='bold'); ax.grid(axis='y', alpha=0.3)

    # Stats table
    ax = axes[1,1]; ax.axis('off')
    tdata = []
    for n in names:
        s = stats[n]
        tdata.append([n.replace('\n',' '), f"{s['PDR']:.2f}%", f"{s['AvgDelay']:.2f}ms",
                      f"{s['Throughput']:.1f}kbps", str(s['DeadFlows']), f"{s['TxPackets']:,}"])
    table = ax.table(cellText=tdata, colLabels=['Phase','PDR','Delay','Throughput','Dead','Tx Pkts'],
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False); table.set_fontsize(9); table.scale(1, 1.8)
    for j in range(6):
        table[0,j].set_facecolor('#2C3E50')
        table[0,j].set_text_props(color='white', fontweight='bold')
    # Highlight best PDR
    best = max(range(len(names)), key=lambda i: list(stats.values())[i]['PDR'])
    for j in range(6): table[best+1,j].set_facecolor('#E8F5E9')
    ax.set_title('Performance Summary', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '08_summary_dashboard.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 08_summary_dashboard.png")

def print_summary(stats):
    print("\n" + "="*75)
    print("  4 PHASE COMPARISON SUMMARY")
    print("="*75)
    print(f"  {'Metric':<18}", end="")
    for n in stats: print(f"{n.replace(chr(10),' '):<18}", end="")
    print(); print("  " + "-"*71)
    for m in ['PDR','AvgDelay','Throughput','DeadFlows','TxPackets','RxPackets']:
        print(f"  {m:<18}", end="")
        for n in stats:
            v = stats[n][m]
            if m=='PDR': print(f"{v:.2f}%{'':<11}", end="")
            elif 'Delay' in m: print(f"{v:.2f}ms{'':<10}", end="")
            elif 'Throughput' in m: print(f"{v:.1f}kbps{'':<8}", end="")
            else: print(f"{v:<18,}", end="")
        print()
    print("="*75)
    print(f"\n  Graphs saved in: {OUTPUT_DIR}/\n")

if __name__ == "__main__":
    print("\n[MIoT] 4 Phase Comparison Analyzer\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    stats = calc_stats(data)

    plot_bar(stats, 'PDR', 'PDR (%)', 'Packet Delivery Ratio Comparison', '01_pdr_comparison.png')
    plot_bar(stats, 'AvgDelay', 'Avg Delay (ms)', 'End-to-End Delay Comparison', '02_delay_comparison.png')
    plot_bar(stats, 'Throughput', 'Throughput (kbps)', 'Throughput Comparison', '03_throughput_comparison.png')
    plot_bar(stats, 'DeadFlows', 'Dead Flows', 'Dead Flows Comparison', '04_dead_flows.png')
    plot_boxplot(data, 'PDR_pct', 'PDR (%)', 'PDR Distribution by Phase', '05_pdr_boxplot.png')
    plot_boxplot(data, 'AvgDelay_ms', 'Delay (ms)', 'Delay Distribution by Phase', '06_delay_boxplot.png')
    plot_packets(stats)
    plot_summary(stats)
    print_summary(stats)
