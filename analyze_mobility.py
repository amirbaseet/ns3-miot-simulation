#!/usr/bin/env python3
"""
Mobility Analysis: Static vs Moving Patients
=============================================
Compares Static / Slow / Normal / Fast mobility
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys

matplotlib.use('Agg')

OUTPUT_DIR = "graphs/mobility"
DPI = 200

CS = '#27AE60'  # Static - Green
CW = '#2E86C1'  # Slow - Blue
CN = '#F39C12'  # Normal - Orange
CF = '#E74C3C'  # Fast - Red

def load_all():
    files = {
        'Static\n(0 m/s)': 'experiments/mobility_static.csv',
        'Slow\n(0.5 m/s)': 'experiments/mobility_slow.csv',
        'Normal\n(1.5 m/s)': 'experiments/mobility_normal.csv',
        'Fast\n(3.0 m/s)': 'experiments/mobility_fast.csv',
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
        }
    return stats

def get_colors(n):
    return [CS, CW, CN, CF][:n]

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
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"[OK] {filename}")

def plot_line(stats):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Impact of Patient Mobility on Network Performance', fontsize=15, fontweight='bold')

    speeds = [0, 0.5, 1.5, 3.0]
    names = list(stats.keys())
    pdr = [stats[n]['PDR'] for n in names]
    delay = [stats[n]['AvgDelay'] for n in names]

    ax1.plot(speeds[:len(pdr)], pdr, 'o-', color='#2E86C1', linewidth=2, markersize=8)
    for i, (s, v) in enumerate(zip(speeds, pdr)):
        ax1.annotate(f'{v:.1f}%', (s, v), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10)
    ax1.set_xlabel('Speed (m/s)', fontsize=12)
    ax1.set_ylabel('PDR (%)', fontsize=12)
    ax1.set_title('PDR vs Mobility Speed', fontweight='bold')
    ax1.grid(alpha=0.3)

    ax2.plot(speeds[:len(delay)], delay, 's-', color='#E74C3C', linewidth=2, markersize=8)
    for i, (s, v) in enumerate(zip(speeds, delay)):
        ax2.annotate(f'{v:.1f}ms', (s, v), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10)
    ax2.set_xlabel('Speed (m/s)', fontsize=12)
    ax2.set_ylabel('Avg Delay (ms)', fontsize=12)
    ax2.set_title('Delay vs Mobility Speed', fontweight='bold')
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05_speed_impact.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 05_speed_impact.png")

def plot_summary(stats):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Mobility Impact Analysis', fontsize=16, fontweight='bold')
    names = list(stats.keys())
    colors = get_colors(len(names))

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

    ax = axes[1,1]; ax.axis('off')
    tdata = []
    for n in names:
        s = stats[n]
        tdata.append([n.replace('\n',' '), f"{s['PDR']:.2f}%", f"{s['AvgDelay']:.2f}ms",
                      str(int(s['DeadFlows'])), f"{s['TxPackets']:,}"])
    table = ax.table(cellText=tdata, colLabels=['Speed','PDR','Delay','Dead','Tx Pkts'],
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
    print("\n" + "="*65)
    print("  MOBILITY COMPARISON")
    print("="*65)
    for n, s in stats.items():
        print(f"  {n.replace(chr(10),' '):<15} PDR={s['PDR']:.2f}%  Delay={s['AvgDelay']:.2f}ms  Dead={s['DeadFlows']}  Tx={s['TxPackets']:,}")
    print("="*65 + "\n")

if __name__ == "__main__":
    print("\n[MIoT] Mobility Analysis\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    stats = calc_stats(data)
    plot_bar(stats, 'PDR', 'PDR (%)', 'PDR by Mobility Speed', '01_pdr.png')
    plot_bar(stats, 'AvgDelay', 'Delay (ms)', 'Delay by Mobility Speed', '02_delay.png')
    plot_bar(stats, 'Throughput', 'Throughput (kbps)', 'Throughput by Mobility Speed', '03_throughput.png')
    plot_bar(stats, 'DeadFlows', 'Dead Flows', 'Dead Flows by Mobility Speed', '04_dead.png')
    plot_line(stats)
    plot_summary(stats)
    print_results(stats)
