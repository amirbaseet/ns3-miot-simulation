#!/usr/bin/env python3
"""
Energy Analysis
================
Reads energy CSV and generates energy consumption graphs
Usage: python3 analyze_energy.py experiments/mqtt-sn-180nodes-broker-results.csv.energy.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys, glob

matplotlib.use('Agg')
OUTPUT_DIR = "graphs/energy"
DPI = 200

def load(path):
    df = pd.read_csv(path)
    print(f"[OK] {path}: {len(df)} nodes")
    return df

def plot_consumption_by_type(df):
    fig, ax = plt.subplots(figsize=(8, 5))
    types = df['Type'].unique()
    colors = {'ECG': '#E74C3C', 'HR': '#2E86C1', 'Temp': '#27AE60', 'CH': '#AF52DE'}
    
    means = []
    labels = []
    cols = []
    for t in ['ECG', 'HR', 'Temp', 'CH']:
        if t in types:
            subset = df[df['Type'] == t]
            means.append(subset['ConsumedEnergy_J'].mean())
            labels.append(t)
            cols.append(colors.get(t, '#666'))
    
    bars = ax.bar(labels, means, color=cols, edgecolor='white', width=0.5, zorder=3)
    for b, v in zip(bars, means):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(means)*0.03,
                f'{v:.3f} J', ha='center', fontweight='bold', fontsize=11)
    
    ax.set_ylabel('Avg Energy Consumed (J)', fontsize=12)
    ax.set_title('Energy Consumption by Node Type', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01_consumption_by_type.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 01_consumption_by_type.png")

def plot_remaining_distribution(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Sensors
    sensors = df[df['Type'] != 'CH']
    ax = axes[0]
    for t, color in [('ECG', '#E74C3C'), ('HR', '#2E86C1'), ('Temp', '#27AE60')]:
        subset = sensors[sensors['Type'] == t]
        if len(subset) > 0:
            ax.hist(subset['RemainingEnergy_J'], bins=20, alpha=0.6, color=color, label=t, edgecolor='white')
    ax.set_xlabel('Remaining Energy (J)', fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('Sensor Energy Distribution', fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # CHs
    chs = df[df['Type'] == 'CH']
    ax = axes[1]
    if len(chs) > 0:
        ax.hist(chs['RemainingEnergy_J'], bins=15, color='#AF52DE', edgecolor='white', alpha=0.7)
    ax.set_xlabel('Remaining Energy (J)', fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('CH Energy Distribution', fontweight='bold')
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02_remaining_distribution.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 02_remaining_distribution.png")

def plot_consumed_pct(df):
    fig, ax = plt.subplots(figsize=(10, 5))
    
    sensors = df[df['Type'] != 'CH'].sort_values('ConsumedPct', ascending=False)
    chs = df[df['Type'] == 'CH'].sort_values('ConsumedPct', ascending=False)
    
    colors_map = {'ECG': '#E74C3C', 'HR': '#2E86C1', 'Temp': '#27AE60'}
    sensor_colors = [colors_map.get(t, '#666') for t in sensors['Type']]
    
    x_sens = range(len(sensors))
    ax.bar(x_sens, sensors['ConsumedPct'], color=sensor_colors, alpha=0.7, width=1.0)
    
    ax.set_xlabel('Node Index (sorted by consumption)', fontsize=11)
    ax.set_ylabel('Energy Consumed (%)', fontsize=11)
    ax.set_title('Per-Node Energy Consumption', fontsize=14, fontweight='bold')
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='#E74C3C', label='ECG'),
                       Patch(facecolor='#2E86C1', label='HR'),
                       Patch(facecolor='#27AE60', label='Temp')]
    ax.legend(handles=legend_elements)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '03_per_node_consumption.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 03_per_node_consumption.png")

def plot_summary(df):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Energy Consumption Analysis', fontsize=16, fontweight='bold')
    
    types = ['ECG', 'HR', 'Temp', 'CH']
    colors = ['#E74C3C', '#2E86C1', '#27AE60', '#AF52DE']
    
    # Avg consumed
    ax = axes[0, 0]
    vals = [df[df['Type']==t]['ConsumedEnergy_J'].mean() for t in types if t in df['Type'].values]
    lbls = [t for t in types if t in df['Type'].values]
    cols = [colors[types.index(t)] for t in lbls]
    bars = ax.bar(lbls, vals, color=cols, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, f'{v:.3f}J', ha='center', fontweight='bold')
    ax.set_title('Avg Consumed (J)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Avg remaining
    ax = axes[0, 1]
    vals = [df[df['Type']==t]['RemainingEnergy_J'].mean() for t in types if t in df['Type'].values]
    bars = ax.bar(lbls, vals, color=cols, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, f'{v:.3f}J', ha='center', fontweight='bold')
    ax.set_title('Avg Remaining (J)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Consumed %
    ax = axes[1, 0]
    vals = [df[df['Type']==t]['ConsumedPct'].mean() for t in types if t in df['Type'].values]
    bars = ax.bar(lbls, vals, color=cols, edgecolor='white', width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(vals)*0.05, f'{v:.1f}%', ha='center', fontweight='bold')
    ax.set_title('Avg Consumed (%)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Table
    ax = axes[1, 1]; ax.axis('off')
    tdata = []
    for t in types:
        if t in df['Type'].values:
            subset = df[df['Type'] == t]
            tdata.append([t, str(len(subset)),
                          f"{subset['InitialEnergy_J'].iloc[0]:.1f}J",
                          f"{subset['RemainingEnergy_J'].mean():.3f}J",
                          f"{subset['ConsumedPct'].mean():.1f}%"])
    table = ax.table(cellText=tdata, colLabels=['Type', 'Count', 'Initial', 'Avg Remain', 'Consumed%'],
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1, 1.8)
    for j in range(5):
        table[0,j].set_facecolor('#2C3E50')
        table[0,j].set_text_props(color='white', fontweight='bold')
    ax.set_title('Summary', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '04_energy_summary.png'), dpi=DPI, bbox_inches='tight')
    plt.close()
    print("[OK] 04_energy_summary.png")

def print_results(df):
    print("\n" + "="*60)
    print("  ENERGY SUMMARY")
    print("="*60)
    for t in ['ECG', 'HR', 'Temp', 'CH']:
        subset = df[df['Type'] == t]
        if len(subset) > 0:
            print(f"  {t:<6} ({len(subset):>3} nodes): "
                  f"Init={subset['InitialEnergy_J'].iloc[0]:.1f}J  "
                  f"Remain={subset['RemainingEnergy_J'].mean():.4f}J  "
                  f"Consumed={subset['ConsumedPct'].mean():.1f}%")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("\n[MIoT] Energy Analysis\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Find energy CSV
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        files = glob.glob('experiments/*.energy.csv')
        if files:
            path = files[0]
        else:
            print("[ERROR] No energy CSV found! Pass as argument or run simulation first.")
            sys.exit(1)
    
    df = load(path)
    plot_consumption_by_type(df)
    plot_remaining_distribution(df)
    plot_consumed_pct(df)
    plot_summary(df)
    print_results(df)
