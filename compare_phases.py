#!/usr/bin/env python3
"""
MIoT Simulation - Comparative Analysis (Phase 1 vs 2 vs 3)
============================================================
Generates comparison graphs across all simulation phases.

Usage:
    python3 compare_phases.py

Input files (in results/ folder):
    - cluster-aodv-nosink-results.csv  (Phase 1)
    - mqtt-sn-results.csv              (Phase 2)
    - mqtt-sn-priority-results.csv     (Phase 3)
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os
import sys

matplotlib.use('Agg')

OUTPUT_DIR = "graphs"
DPI = 200

# Colors
C1 = '#E74C3C'  # Phase 1 - Red
C2 = '#2E86C1'  # Phase 2 - Blue
C3 = '#27AE60'  # Phase 3 - Green
BG = '#F8F9FA'

def load_all():
    """Load all 3 CSV files."""
    files = {
        'Phase 1\n(OnOff)': 'results/cluster-aodv-nosink-results.csv',
        'Phase 2\n(MQTT-SN)': 'results/mqtt-sn-results.csv',
        'Phase 3\n(Priority)': 'results/mqtt-sn-priority-results.csv',
    }

    data = {}
    for name, path in files.items():
        if os.path.exists(path):
            data[name] = pd.read_csv(path)
            print(f"[OK] {name.replace(chr(10),' ')}: {len(data[name])} flows from {path}")
        else:
            print(f"[WARN] {path} not found, skipping")

    if len(data) == 0:
        print("[ERROR] No data files found!")
        sys.exit(1)

    return data

def calc_stats(data):
    """Calculate summary stats for each phase."""
    stats = {}
    for name, df in data.items():
        total_tx = df['TxPackets'].sum()
        total_rx = df['RxPackets'].sum()
        stats[name] = {
            'PDR': total_rx / total_tx * 100 if total_tx > 0 else 0,
            'AvgDelay': df['AvgDelay_ms'][df['AvgDelay_ms'] > 0].mean() if len(df[df['AvgDelay_ms'] > 0]) > 0 else 0,
            'Throughput': df['Throughput_kbps'].mean(),
            'DeadFlows': len(df[df['RxPackets'] == 0]),
            'TotalFlows': len(df),
            'TxPackets': total_tx,
            'RxPackets': total_rx,
            'LostPackets': total_tx - total_rx,
            'AvgJitter': df['AvgJitter_ms'][df['AvgJitter_ms'] > 0].mean() if len(df[df['AvgJitter_ms'] > 0]) > 0 else 0,
        }
    return stats

# ============================================================
#  GRAPH 1: PDR Comparison Bar Chart
# ============================================================
def plot_pdr_comparison(stats):
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('white')

    names = list(stats.keys())
    values = [stats[n]['PDR'] for n in names]
    colors = [C1, C2, C3][:len(names)]

    bars = ax.bar(names, values, color=colors, edgecolor='white', width=0.5, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.2f}%', ha='center', va='bottom', fontweight='bold', fontsize=13)

    ax.set_ylabel('Packet Delivery Ratio (%)', fontsize=12)
    ax.set_title('PDR Comparison Across Phases', fontsize=15, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3, zorder=0)
    ax.axhline(y=100, color='gray', linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01_pdr_comparison.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 01_pdr_comparison.png")

# ============================================================
#  GRAPH 2: Delay Comparison
# ============================================================
def plot_delay_comparison(stats):
    fig, ax = plt.subplots(figsize=(8, 5))

    names = list(stats.keys())
    values = [stats[n]['AvgDelay'] for n in names]
    colors = [C1, C2, C3][:len(names)]

    bars = ax.bar(names, values, color=colors, edgecolor='white', width=0.5, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.03,
                f'{val:.2f} ms', ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax.set_ylabel('Average End-to-End Delay (ms)', fontsize=12)
    ax.set_title('Delay Comparison Across Phases', fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02_delay_comparison.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 02_delay_comparison.png")

# ============================================================
#  GRAPH 3: Throughput Comparison
# ============================================================
def plot_throughput_comparison(stats):
    fig, ax = plt.subplots(figsize=(8, 5))

    names = list(stats.keys())
    values = [stats[n]['Throughput'] for n in names]
    colors = [C1, C2, C3][:len(names)]

    bars = ax.bar(names, values, color=colors, edgecolor='white', width=0.5, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.03,
                f'{val:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax.set_ylabel('Average Throughput (kbps)', fontsize=12)
    ax.set_title('Throughput Comparison Across Phases', fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '03_throughput_comparison.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 03_throughput_comparison.png")

# ============================================================
#  GRAPH 4: Dead Flows
# ============================================================
def plot_dead_flows(stats):
    fig, ax = plt.subplots(figsize=(8, 5))

    names = list(stats.keys())
    values = [stats[n]['DeadFlows'] for n in names]
    colors = [C1, C2, C3][:len(names)]

    bars = ax.bar(names, values, color=colors, edgecolor='white', width=0.5, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.03,
                str(val), ha='center', va='bottom', fontweight='bold', fontsize=13)

    ax.set_ylabel('Number of Dead Flows (0 packets received)', fontsize=12)
    ax.set_title('Dead Flows Comparison', fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '04_dead_flows.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 04_dead_flows.png")

# ============================================================
#  GRAPH 5: PDR Distribution (Box Plot)
# ============================================================
def plot_pdr_boxplot(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    plot_data = []
    labels = []
    colors = [C1, C2, C3]

    for name, df in data.items():
        plot_data.append(df['PDR_pct'].dropna())
        labels.append(name)

    bp = ax.boxplot(plot_data, labels=labels, patch_artist=True, widths=0.4,
                    medianprops=dict(color='black', linewidth=2),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5))

    for patch, color in zip(bp['boxes'], colors[:len(plot_data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel('PDR (%)', fontsize=12)
    ax.set_title('PDR Distribution by Phase', fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05_pdr_boxplot.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 05_pdr_boxplot.png")

# ============================================================
#  GRAPH 6: Delay Distribution (Box Plot)
# ============================================================
def plot_delay_boxplot(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    plot_data = []
    labels = []
    colors = [C1, C2, C3]

    for name, df in data.items():
        d = df['AvgDelay_ms'].dropna()
        d = d[d > 0]
        plot_data.append(d)
        labels.append(name)

    bp = ax.boxplot(plot_data, labels=labels, patch_artist=True, widths=0.4,
                    medianprops=dict(color='black', linewidth=2),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5))

    for patch, color in zip(bp['boxes'], colors[:len(plot_data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel('Average Delay (ms)', fontsize=12)
    ax.set_title('Delay Distribution by Phase', fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '06_delay_boxplot.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 06_delay_boxplot.png")

# ============================================================
#  GRAPH 7: Packet Loss Comparison (Stacked Bar)
# ============================================================
def plot_packet_stats(stats):
    fig, ax = plt.subplots(figsize=(8, 5))

    names = list(stats.keys())
    rx = [stats[n]['RxPackets'] for n in names]
    lost = [stats[n]['LostPackets'] for n in names]

    x = np.arange(len(names))
    w = 0.4

    bars1 = ax.bar(x, rx, w, label='Delivered', color=C3, edgecolor='white', zorder=3)
    bars2 = ax.bar(x, lost, w, bottom=rx, label='Lost', color=C1, edgecolor='white', zorder=3)

    for i, (r, l) in enumerate(zip(rx, lost)):
        total = r + l
        pct = r / total * 100 if total > 0 else 0
        ax.text(i, total + max(rx)*0.02, f'{pct:.1f}%', ha='center', fontweight='bold', fontsize=11)

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel('Packets', fontsize=12)
    ax.set_title('Delivered vs Lost Packets', fontsize=15, fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, zorder=0)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07_packet_stats.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 07_packet_stats.png")

# ============================================================
#  GRAPH 8: Summary Dashboard
# ============================================================
def plot_summary(stats):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('MIoT Simulation — Phase Comparison Dashboard', fontsize=18, fontweight='bold')

    names = list(stats.keys())
    colors = [C1, C2, C3][:len(names)]

    # PDR
    ax = axes[0, 0]
    vals = [stats[n]['PDR'] for n in names]
    bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.5, f'{v:.1f}%', ha='center', fontweight='bold')
    ax.set_title('PDR (%)', fontweight='bold')
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    # Delay
    ax = axes[0, 1]
    vals = [stats[n]['AvgDelay'] for n in names]
    bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, f'{v:.1f}ms', ha='center', fontweight='bold')
    ax.set_title('Avg Delay (ms)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Dead Flows
    ax = axes[1, 0]
    vals = [stats[n]['DeadFlows'] for n in names]
    bars = ax.bar(names, vals, color=colors, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, str(v), ha='center', fontweight='bold')
    ax.set_title('Dead Flows', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Stats table
    ax = axes[1, 1]
    ax.axis('off')
    table_data = []
    for n in names:
        s = stats[n]
        table_data.append([
            n.replace('\n', ' '),
            f"{s['PDR']:.2f}%",
            f"{s['AvgDelay']:.2f} ms",
            f"{s['Throughput']:.1f} kbps",
            str(s['DeadFlows']),
            f"{s['TxPackets']:,}",
        ])
    table = ax.table(
        cellText=table_data,
        colLabels=['Phase', 'PDR', 'Delay', 'Throughput', 'Dead', 'Tx Pkts'],
        loc='center', cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)
    for j in range(6):
        table[0, j].set_facecolor('#2C3E50')
        table[0, j].set_text_props(color='white', fontweight='bold')
    # Highlight best PDR row
    best_idx = max(range(len(names)), key=lambda i: list(stats.values())[i]['PDR'])
    for j in range(6):
        table[best_idx+1, j].set_facecolor('#E8F5E9')
    ax.set_title('Performance Summary', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '08_summary_dashboard.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 08_summary_dashboard.png")

# ============================================================
def print_summary(stats):
    print("\n" + "=" * 70)
    print("  PHASE COMPARISON SUMMARY")
    print("=" * 70)
    print(f"  {'Metric':<20} ", end="")
    for n in stats: print(f"{n.replace(chr(10),' '):<20} ", end="")
    print()
    print("  " + "-" * 66)
    for metric in ['PDR', 'AvgDelay', 'Throughput', 'DeadFlows', 'TxPackets', 'RxPackets']:
        print(f"  {metric:<20} ", end="")
        for n in stats:
            v = stats[n][metric]
            if metric == 'PDR': print(f"{v:.2f}%{'':<14} ", end="")
            elif 'Delay' in metric or 'Jitter' in metric: print(f"{v:.2f} ms{'':<12} ", end="")
            elif 'Throughput' in metric: print(f"{v:.2f} kbps{'':<10} ", end="")
            else: print(f"{v:<20,} ", end="")
        print()
    print("=" * 70)
    print(f"\n  Graphs saved in: {OUTPUT_DIR}/\n")

# ============================================================
if __name__ == "__main__":
    print("\n[MIoT] Phase Comparison Analyzer\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    stats = calc_stats(data)

    plot_pdr_comparison(stats)
    plot_delay_comparison(stats)
    plot_throughput_comparison(stats)
    plot_dead_flows(stats)
    plot_pdr_boxplot(data)
    plot_delay_boxplot(data)
    plot_packet_stats(stats)
    plot_summary(stats)
    print_summary(stats)
