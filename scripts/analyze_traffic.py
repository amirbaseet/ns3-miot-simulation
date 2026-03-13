#!/usr/bin/env python3
"""
Traffic Load Analysis
======================
Compares Low / Medium / High ECG traffic ratios
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys

matplotlib.use('Agg')

OUTPUT_DIR = "graphs/traffic"
DPI = 200

CL = '#27AE60'   # Low - Green
CM = '#2E86C1'   # Medium - Blue
CH = '#E74C3C'   # High - Red

def load_all():
    files = {
        'Low\n(20 ECG)': 'experiments/traffic_low.csv',
        'Medium\n(60 ECG)': 'experiments/traffic_medium.csv',
        'High\n(140 ECG)': 'experiments/traffic_high.csv',
    }
    data = {}
    for name, path in files.items():
        if os.path.exists(path):
            data[name] = pd.read_csv(path)
            print(f"[OK] {name.replace(chr(10),' ')}: {len(data[name])} flows")
        else:
            print(f"[SKIP] {path}")
    if len(data) == 0:
        print("[ERROR] No data!"); sys.exit(1)
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
            'TxPackets': tx, 'RxPackets': rx,
            'LostPackets': tx - rx,
        }
    return stats

def plot_bar(stats, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    names = list(stats.keys())
    values = [stats[n][metric] for n in names]
    colors = [CL, CM, CH][:len(names)]
    bars = ax.bar(names, values, color=colors, edgecolor='white', width=0.5, zorder=3)
    for b, v in zip(bars, values):
        fmt = f'{v:.2f}%' if 'PDR' in metric else f'{v:.2f} ms' if 'Delay' in metric else f'{v:.1f}' if 'Throughput' in metric else str(int(v))
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(values)*0.03, fmt, ha='center', fontweight='bold', fontsize=11)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

def plot_packets(stats):
    fig, ax = plt.subplots(figsize=(8, 5))
    names = list(stats.keys())
    rx = [stats[n]['RxPackets'] for n in names]
    lost = [stats[n]['LostPackets'] for n in names]
    colors_d = [CL, CM, CH]
    x = np.arange(len(names))
    ax.bar(x, rx, 0.4, label='Delivered', color='#27AE60', edgecolor='white', zorder=3)
    ax.bar(x, lost, 0.4, bottom=rx, label='Lost', color='#E74C3C', edgecolor='white', zorder=3)
    for i, (r, l) in enumerate(zip(rx, lost)):
        total = r + l
        pct = r/total*100 if total > 0 else 0
        ax.text(i, total+max(rx)*0.02, f'{pct:.1f}%', ha='center', fontweight='bold', fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel('Packets', fontsize=12)
    ax.set_title('Delivered vs Lost by Traffic Load', fontsize=14, fontweight='bold')
    ax.legend(); ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05_packets.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 05_packets.png")

def plot_summary(stats):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Traffic Load Impact Analysis', fontsize=16, fontweight='bold')
    names = list(stats.keys())
    colors = [CL, CM, CH][:len(names)]

    for ax, metric, title in zip(
        [axes[0,0], axes[0,1], axes[1,0]],
        ['PDR', 'AvgDelay', 'DeadFlows'],
        ['PDR (%)', 'Avg Delay (ms)', 'Dead Flows']):
        vals = [stats[n][metric] for n in names]
        bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
        for b, v in zip(bars, vals):
            fmt = f'{v:.1f}%' if 'PDR' in metric else f'{v:.1f}ms' if 'Delay' in metric else str(int(v))
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, fmt, ha='center', fontweight='bold')
        ax.set_title(title, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

    # Table
    ax = axes[1,1]; ax.axis('off')
    tdata = []
    for n in names:
        s = stats[n]
        tdata.append([n.replace('\n',' '), f"{s['PDR']:.2f}%", f"{s['AvgDelay']:.2f}ms",
                      str(int(s['DeadFlows'])), f"{s['TxPackets']:,}"])
    table = ax.table(cellText=tdata, colLabels=['Load','PDR','Delay','Dead','Tx Pkts'],
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1, 1.8)
    for j in range(5):
        table[0,j].set_facecolor('#2C3E50')
        table[0,j].set_text_props(color='white', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '06_summary.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 06_summary.png")

def print_results(stats):
    print("\n" + "="*60)
    print("  TRAFFIC LOAD COMPARISON")
    print("="*60)
    for n, s in stats.items():
        print(f"  {n.replace(chr(10),' '):<15} PDR={s['PDR']:.2f}%  Delay={s['AvgDelay']:.2f}ms  Dead={s['DeadFlows']}  Tx={s['TxPackets']:,}")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("\n[MIoT] Traffic Load Analysis\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    stats = calc_stats(data)
    plot_bar(stats, 'PDR', 'PDR (%)', 'PDR by Traffic Load', '01_pdr.png')
    plot_bar(stats, 'AvgDelay', 'Delay (ms)', 'Delay by Traffic Load', '02_delay.png')
    plot_bar(stats, 'Throughput', 'Throughput (kbps)', 'Throughput by Traffic Load', '03_throughput.png')
    plot_bar(stats, 'DeadFlows', 'Dead Flows', 'Dead Flows by Traffic Load', '04_dead.png')
    plot_packets(stats)
    plot_summary(stats)
    print_results(stats)
