#!/usr/bin/env python3
"""
Cluster-Based AODV - Results Analyzer
======================================
Auto-detects CSV file (sink or nosink version).
Generates 6 performance graphs.

Usage:
    python3 analyze_results.py
    python3 analyze_results.py cluster-aodv-results.csv
    python3 analyze_results.py cluster-aodv-nosink-results.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os
import sys

matplotlib.use('Agg')

# ============================================================
OUTPUT_DIR = "results"
DPI = 150

C = {
    'blue': '#2E5090', 'red': '#E74C3C', 'green': '#27AE60',
    'orange': '#F39C12', 'purple': '#8E44AD', 'gray': '#7F8C8D',
    'teal': '#1ABC9C', 'dark': '#2C3E50',
}

def find_csv():
    """Auto-detect CSV file or use command line argument."""
    if len(sys.argv) > 1:
        f = sys.argv[1]
        if os.path.exists(f):
            return f
        print(f"[ERROR] {f} not found!")
        sys.exit(1)

    # Auto-detect
    candidates = [
        "cluster-aodv-nosink-results.csv",
        "cluster-aodv-results.csv",
    ]
    for f in candidates:
        if os.path.exists(f):
            return f

    print("[ERROR] No CSV file found! Run simulation first.")
    sys.exit(1)

def setup():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data(csv_file):
    df = pd.read_csv(csv_file)
    print(f"[INFO] Loaded {len(df)} flows from {csv_file}")
    return df

# ============================================================
#  GRAPHS
# ============================================================

def plot_throughput(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Throughput Analysis', fontsize=16, fontweight='bold', y=1.02)

    data = df['Throughput_kbps']
    mean = data.mean()

    axes[0].hist(data, bins=30, color=C['blue'], edgecolor='white', alpha=0.85)
    axes[0].axvline(mean, color=C['red'], linestyle='--', lw=2, label=f"Ortalama: {mean:.2f} kbps")
    axes[0].set_xlabel('Throughput (kbps)')
    axes[0].set_ylabel('Akış Sayısı')
    axes[0].set_title('Throughput Dağılımı')
    axes[0].legend()

    bp = axes[1].boxplot(data.dropna(), vert=True, patch_artist=True,
                         boxprops=dict(facecolor=C['blue'], alpha=0.6),
                         medianprops=dict(color=C['red'], lw=2),
                         whiskerprops=dict(color=C['dark']),
                         capprops=dict(color=C['dark']))
    axes[1].set_ylabel('Throughput (kbps)')
    axes[1].set_title('Throughput Box Plot')
    axes[1].set_xticklabels(['Tüm Akışlar'])

    # Add stats text
    stats_text = f"Min: {data.min():.2f}\nMax: {data.max():.2f}\nOrt: {mean:.2f}\nStd: {data.std():.2f}"
    axes[1].text(1.3, data.median(), stats_text, fontsize=9, va='center',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'throughput.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] throughput.png")

def plot_pdr(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Packet Delivery Ratio (PDR) Analysis', fontsize=16, fontweight='bold', y=1.02)

    data = df['PDR_pct']
    mean = data.mean()

    axes[0].hist(data, bins=25, color=C['green'], edgecolor='white', alpha=0.85)
    axes[0].axvline(mean, color=C['red'], linestyle='--', lw=2, label=f"Ortalama: {mean:.2f}%")
    axes[0].set_xlabel('PDR (%)')
    axes[0].set_ylabel('Akış Sayısı')
    axes[0].set_title('PDR Dağılımı')
    axes[0].legend()

    # Category breakdown
    cats = ['100%', '90-99%', '50-89%', '<50%', '0%']
    counts = [
        len(df[df['PDR_pct'] == 100]),
        len(df[(df['PDR_pct'] >= 90) & (df['PDR_pct'] < 100)]),
        len(df[(df['PDR_pct'] >= 50) & (df['PDR_pct'] < 90)]),
        len(df[(df['PDR_pct'] > 0) & (df['PDR_pct'] < 50)]),
        len(df[df['PDR_pct'] == 0]),
    ]
    colors = [C['green'], C['teal'], C['orange'], C['red'], C['dark']]
    bars = axes[1].bar(cats, counts, color=colors, edgecolor='white')
    axes[1].set_xlabel('PDR Aralığı')
    axes[1].set_ylabel('Akış Sayısı')
    axes[1].set_title('PDR Kategori Dağılımı')
    for i, v in enumerate(counts):
        if v > 0:
            axes[1].text(i, v + max(counts)*0.02, str(v), ha='center', fontweight='bold', fontsize=10)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'pdr.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] pdr.png")

def plot_delay(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('End-to-End Delay Analysis', fontsize=16, fontweight='bold', y=1.02)

    data = df['AvgDelay_ms'].dropna()
    data = data[data > 0]

    if len(data) > 0:
        axes[0].hist(data, bins=30, color=C['orange'], edgecolor='white', alpha=0.85)
        mean = data.mean()
        axes[0].axvline(mean, color=C['red'], linestyle='--', lw=2, label=f"Ortalama: {mean:.2f} ms")
        axes[0].set_xlabel('Ortalama Gecikme (ms)')
        axes[0].set_ylabel('Akış Sayısı')
        axes[0].set_title('Gecikme Dağılımı')
        axes[0].legend()

    # Delay vs Throughput scatter
    valid = df[(df['Throughput_kbps'] > 0) & (df['AvgDelay_ms'] > 0)]
    if len(valid) > 0:
        scatter = axes[1].scatter(valid['Throughput_kbps'], valid['AvgDelay_ms'],
                                  c=valid['PDR_pct'], cmap='RdYlGn', alpha=0.5, s=15,
                                  vmin=0, vmax=100)
        plt.colorbar(scatter, ax=axes[1], label='PDR (%)')
        axes[1].set_xlabel('Throughput (kbps)')
        axes[1].set_ylabel('Ortalama Gecikme (ms)')
        axes[1].set_title('Gecikme vs Throughput (renk = PDR)')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'delay.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] delay.png")

def plot_jitter(df):
    fig, ax = plt.subplots(figsize=(10, 5))

    data = df['AvgJitter_ms'].dropna()
    data = data[data > 0]

    if len(data) > 0:
        ax.hist(data, bins=30, color=C['purple'], edgecolor='white', alpha=0.85)
        mean = data.mean()
        ax.axvline(mean, color=C['red'], linestyle='--', lw=2, label=f"Ortalama: {mean:.2f} ms")
        ax.set_xlabel('Ortalama Jitter (ms)')
        ax.set_ylabel('Akış Sayısı')
        ax.set_title('Jitter Dağılımı', fontsize=14, fontweight='bold')
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'jitter.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] jitter.png")

def plot_packet_loss(df):
    fig, ax = plt.subplots(figsize=(10, 6))

    top = df.sort_values('LostPackets', ascending=False).head(25)
    if len(top) > 0 and top['LostPackets'].sum() > 0:
        y_pos = range(len(top))
        bars = ax.barh(y_pos, top['LostPackets'], color=C['red'], alpha=0.8)
        ax.set_xlabel('Kayıp Paket Sayısı')
        ax.set_ylabel('Akış')
        ax.set_title('En Çok Paket Kaybeden 25 Akış', fontsize=14, fontweight='bold')
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"F{fid}" for fid in top['FlowID']], fontsize=7)
        ax.invert_yaxis()
    else:
        ax.text(0.5, 0.5, 'Paket kaybı yok!', transform=ax.transAxes,
                ha='center', va='center', fontsize=16, color=C['green'])
        ax.set_title('Paket Kaybı Analizi', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'packet_loss.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] packet_loss.png")

def plot_overall_summary(df):
    """Single summary figure with key metrics."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Simülasyon Genel Özet', fontsize=18, fontweight='bold')

    # 1. PDR pie chart
    delivered = df['RxPackets'].sum()
    lost = df['LostPackets'].sum()
    if delivered + lost > 0:
        axes[0, 0].pie([delivered, lost], labels=['Teslim Edilen', 'Kayıp'],
                       colors=[C['green'], C['red']], autopct='%1.1f%%',
                       startangle=90, textprops={'fontsize': 11})
        axes[0, 0].set_title(f'Genel PDR: {delivered/(delivered+lost)*100:.1f}%', fontweight='bold')

    # 2. Throughput per-flow distribution
    valid_tput = df['Throughput_kbps'][df['Throughput_kbps'] > 0]
    if len(valid_tput) > 0:
        axes[0, 1].hist(valid_tput, bins=20, color=C['blue'], edgecolor='white', alpha=0.8)
        axes[0, 1].set_xlabel('Throughput (kbps)')
        axes[0, 1].set_ylabel('Akış Sayısı')
        axes[0, 1].set_title(f'Throughput (Ort: {valid_tput.mean():.2f} kbps)', fontweight='bold')

    # 3. Delay CDF
    valid_delay = df['AvgDelay_ms'][(df['AvgDelay_ms'] > 0)].sort_values()
    if len(valid_delay) > 0:
        cdf = np.arange(1, len(valid_delay) + 1) / len(valid_delay) * 100
        axes[1, 0].plot(valid_delay.values, cdf, color=C['orange'], lw=2)
        axes[1, 0].set_xlabel('Gecikme (ms)')
        axes[1, 0].set_ylabel('Kümülatif %')
        axes[1, 0].set_title(f'Gecikme CDF (Ort: {valid_delay.mean():.1f} ms)', fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axhline(y=90, color=C['red'], linestyle=':', alpha=0.5, label='%90')
        axes[1, 0].legend()

    # 4. Stats table
    axes[1, 1].axis('off')
    total_tx = df['TxPackets'].sum()
    total_rx = df['RxPackets'].sum()
    total_lost = df['LostPackets'].sum()
    overall_pdr = total_rx / total_tx * 100 if total_tx > 0 else 0

    stats = [
        ['Toplam Akış', f"{len(df)}"],
        ['Ölü Akış (0 Rx)', f"{len(df[df['RxPackets']==0])}"],
        ['Gönderilen Paket', f"{total_tx:,}"],
        ['Alınan Paket', f"{total_rx:,}"],
        ['Kayıp Paket', f"{total_lost:,}"],
        ['Genel PDR', f"{overall_pdr:.2f}%"],
        ['Ort. Throughput', f"{df['Throughput_kbps'].mean():.2f} kbps"],
        ['Ort. Gecikme', f"{df['AvgDelay_ms'].mean():.2f} ms"],
        ['Ort. Jitter', f"{df['AvgJitter_ms'].mean():.2f} ms"],
    ]
    table = axes[1, 1].table(cellText=stats, colLabels=['Metrik', 'Değer'],
                              loc='center', cellLoc='left')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.5)
    # Header style
    for j in range(2):
        table[0, j].set_facecolor(C['dark'])
        table[0, j].set_text_props(color='white', fontweight='bold')
    axes[1, 1].set_title('Performans Özeti', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'summary.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] summary.png")

def print_summary(df):
    total_tx = df['TxPackets'].sum()
    total_rx = df['RxPackets'].sum()
    pdr = total_rx / total_tx * 100 if total_tx > 0 else 0

    print("\n" + "=" * 55)
    print("  SİMÜLASYON SONUÇ ÖZETİ")
    print("=" * 55)
    print(f"  Toplam Akış       : {len(df)}")
    print(f"  Ölü Akış (0 Rx)   : {len(df[df['RxPackets']==0])}")
    print(f"  Tx Paket          : {total_tx:,}")
    print(f"  Rx Paket          : {total_rx:,}")
    print(f"  Kayıp             : {total_tx - total_rx:,}")
    print(f"  ---")
    print(f"  PDR               : {pdr:.2f}%")
    print(f"  Ort. Throughput   : {df['Throughput_kbps'].mean():.2f} kbps")
    print(f"  Ort. Gecikme      : {df['AvgDelay_ms'].mean():.2f} ms")
    print(f"  Ort. Jitter       : {df['AvgJitter_ms'].mean():.2f} ms")
    print("=" * 55)
    print(f"  Grafikler: {OUTPUT_DIR}/")
    print(f"  (throughput, pdr, delay, jitter, packet_loss, summary)")
    print()

# ============================================================
if __name__ == "__main__":
    print("\n[Cluster-Based AODV] Results Analyzer\n")
    csv_file = find_csv()
    setup()
    df = load_data(csv_file)
    plot_throughput(df)
    plot_pdr(df)
    plot_delay(df)
    plot_jitter(df)
    plot_packet_loss(df)
    plot_overall_summary(df)
    print_summary(df)
