#!/usr/bin/env python3
"""
WSN vs MQTT-SN Statistical Comparison Analysis
================================================
Reads multiple seeds, calculates mean +/- std, 95% CI
Falls back to single-run data if statistical data unavailable

Usage: python3 scripts/analyze_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys, glob

matplotlib.use('Agg')

OUTPUT_DIR = "graphs/comparison"
DPI = 200
NODES = [50, 100, 150, 200]
MAX_SEEDS = 10

C_WSN = '#E74C3C'
C_MQTT = '#2E86C1'

def load_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

def calc_metrics(df):
    if df is None: return None
    tx = df['TxPackets'].sum()
    rx = df['RxPackets'].sum()
    d = df['AvgDelay_ms'][df['AvgDelay_ms'] > 0]
    return {
        'PDR': rx/tx*100 if tx > 0 else 0,
        'Delay': d.mean() if len(d) > 0 else 0,
        'Throughput': df['Throughput_kbps'].mean(),
        'Dead': len(df[df['RxPackets'] == 0]),
    }

def load_all():
    results = {}
    for s in [1, 2]:
        for sc in ['wsn', 'mqtt']:
            for n in NODES:
                key = f"exp{s}_{sc}_{n}"
                runs = []
                for r in range(1, MAX_SEEDS + 1):
                    path = f"experiments/statistical/{key}_r{r}.csv"
                    df = load_csv(path)
                    if df is not None:
                        m = calc_metrics(df)
                        if m: runs.append(m)
                if len(runs) == 0:
                    path = f"experiments/comparison/{key}.csv"
                    df = load_csv(path)
                    if df is not None:
                        m = calc_metrics(df)
                        if m: runs.append(m)
                if len(runs) > 0:
                    results[key] = {
                        'n_runs': len(runs),
                        'PDR_mean': np.mean([r['PDR'] for r in runs]),
                        'PDR_std': np.std([r['PDR'] for r in runs], ddof=1) if len(runs) > 1 else 0,
                        'Delay_mean': np.mean([r['Delay'] for r in runs]),
                        'Delay_std': np.std([r['Delay'] for r in runs], ddof=1) if len(runs) > 1 else 0,
                        'Dead_mean': np.mean([r['Dead'] for r in runs]),
                        'Dead_std': np.std([r['Dead'] for r in runs], ddof=1) if len(runs) > 1 else 0,
                        'Throughput_mean': np.mean([r['Throughput'] for r in runs]),
                    }
                    print(f"[OK] {key}: {len(runs)} runs")
    return results

def plot_bars(data, setnum, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    p = f"exp{setnum}"
    wm = [data.get(f"{p}_wsn_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ws = [data.get(f"{p}_wsn_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    mm = [data.get(f"{p}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ms = [data.get(f"{p}_mqtt_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    x = np.arange(len(NODES)); w = 0.3
    ax.bar(x-w/2, wm, w, yerr=ws, capsize=5, label='WSN', color=C_WSN, edgecolor='white', zorder=3, alpha=0.85)
    ax.bar(x+w/2, mm, w, yerr=ms, capsize=5, label='MQTT-SN', color=C_MQTT, edgecolor='white', zorder=3, alpha=0.85)
    mv = max(max(wm), max(mm)) if wm and mm else 1
    for i in range(len(NODES)):
        f1 = f'{wm[i]:.1f}' if metric != 'Dead' else f'{wm[i]:.0f}'
        f2 = f'{mm[i]:.1f}' if metric != 'Dead' else f'{mm[i]:.0f}'
        ax.text(x[i]-w/2, wm[i]+ws[i]+mv*0.02, f1, ha='center', fontsize=7, color=C_WSN, fontweight='bold')
        ax.text(x[i]+w/2, mm[i]+ms[i]+mv*0.02, f2, ha='center', fontsize=7, color=C_MQTT, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels([f'{n}' for n in NODES])
    ax.set_xlabel('Nodes'); ax.set_ylabel(ylabel)
    sn = "No Broker" if setnum == 1 else "With Broker"
    nr = data.get(f"{p}_wsn_50", {}).get('n_runs', 1)
    ax.set_title(f'{title} - {sn} ({nr} runs, mean+/-std)', fontsize=12, fontweight='bold')
    ax.legend(); ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight'); plt.close()
    print(f"[OK] {filename}")

def plot_lines(data, setnum, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    p = f"exp{setnum}"
    wm = [data.get(f"{p}_wsn_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ws = [data.get(f"{p}_wsn_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    mm = [data.get(f"{p}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ms = [data.get(f"{p}_mqtt_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    ax.plot(NODES, wm, 'o-', color=C_WSN, linewidth=2, markersize=8, label='WSN')
    ax.fill_between(NODES, [m-s for m,s in zip(wm,ws)], [m+s for m,s in zip(wm,ws)], color=C_WSN, alpha=0.15)
    ax.plot(NODES, mm, 's-', color=C_MQTT, linewidth=2, markersize=8, label='MQTT-SN')
    ax.fill_between(NODES, [m-s for m,s in zip(mm,ms)], [m+s for m,s in zip(mm,ms)], color=C_MQTT, alpha=0.15)
    for i in range(len(NODES)):
        ax.annotate(f'{wm[i]:.1f}', (NODES[i], wm[i]), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9, color=C_WSN)
        ax.annotate(f'{mm[i]:.1f}', (NODES[i], mm[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color=C_MQTT)
    ax.set_xlabel('Nodes'); ax.set_ylabel(ylabel)
    sn = "No Broker" if setnum == 1 else "With Broker"
    ax.set_title(f'{title} - {sn} (shaded=+/-1std)', fontsize=12, fontweight='bold')
    ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight'); plt.close()
    print(f"[OK] {filename}")

def plot_dashboard(data):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('WSN vs MQTT-SN Statistical Dashboard', fontsize=18, fontweight='bold')
    scen = [('exp1_wsn','WSN No Sink',C_WSN,'o-'),('exp1_mqtt','MQTT-SN No Broker',C_MQTT,'s-'),
            ('exp2_wsn','WSN With Sink','#F5B7B1','o--'),('exp2_mqtt','MQTT-SN With Broker','#AED6F1','s--')]
    for ax, m, yl, t in [(axes[0,0],'PDR','PDR (%)','PDR'),(axes[0,1],'Delay','Delay (ms)','Delay'),
                          (axes[1,0],'Throughput','kbps','Throughput'),(axes[1,1],'Dead','Dead Flows','Dead Flows')]:
        for pf, lb, cl, st in scen:
            mn = [data.get(f"{pf}_{n}",{}).get(f'{m}_mean',0) for n in NODES]
            sd = [data.get(f"{pf}_{n}",{}).get(f'{m}_std',0) for n in NODES]
            ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, linewidth=2, markersize=6, label=lb, capsize=3)
        ax.set_xlabel('Nodes'); ax.set_ylabel(yl); ax.set_title(t, fontweight='bold')
        ax.set_xticks(NODES); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, '10_master_dashboard.png'), dpi=DPI, bbox_inches='tight'); plt.close()
    print("[OK] 10_master_dashboard.png")

def plot_table(data):
    fig, ax = plt.subplots(figsize=(16, 9)); ax.axis('off')
    hd = ['Set','Nodes','Runs','WSN PDR','MQTT PDR','WSN Delay','MQTT Delay','Winner']
    rows = []
    for s in [1,2]:
        sn = "No Broker" if s==1 else "With Broker"
        for n in NODES:
            w = data.get(f"exp{s}_wsn_{n}",{}); m = data.get(f"exp{s}_mqtt_{n}",{})
            nr = w.get('n_runs',0)
            wp = f"{w.get('PDR_mean',0):.1f}+/-{w.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            wd = f"{w.get('Delay_mean',0):.1f}+/-{w.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            win = "MQTT-SN" if m.get('PDR_mean',0) > w.get('PDR_mean',0)+1 else "WSN" if w.get('PDR_mean',0)>m.get('PDR_mean',0)+1 else "~Tie"
            rows.append([sn,str(n),str(nr),wp,mp,wd,md,win])
    tb = ax.table(cellText=rows, colLabels=hd, loc='center', cellLoc='center')
    tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.8)
    for j in range(len(hd)):
        tb[0,j].set_facecolor('#2C3E50'); tb[0,j].set_text_props(color='white', fontweight='bold')
    for i in range(1,len(rows)+1):
        if rows[i-1][-1]=="MQTT-SN":
            for j in range(len(hd)): tb[i,j].set_facecolor('#D6EAF8')
        elif rows[i-1][-1]=="WSN":
            for j in range(len(hd)): tb[i,j].set_facecolor('#FADBD8')
    ax.set_title('Statistical Summary (mean +/- std)', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, '11_summary_table.png'), dpi=DPI, bbox_inches='tight'); plt.close()
    print("[OK] 11_summary_table.png")

def print_results(data):
    print("\n" + "="*90)
    print("  WSN vs MQTT-SN STATISTICAL COMPARISON")
    print("="*90)
    for s in [1,2]:
        sn = "NO BROKER" if s==1 else "WITH BROKER"
        print(f"\n  --- SET {s}: {sn} ---")
        print(f"  {'Nodes':<8} {'Runs':<6} {'WSN PDR':<20} {'MQTT PDR':<20} {'Winner'}")
        print("  "+"-"*64)
        for n in NODES:
            w = data.get(f"exp{s}_wsn_{n}",{}); m = data.get(f"exp{s}_mqtt_{n}",{})
            nr = w.get('n_runs',0)
            wp = f"{w.get('PDR_mean',0):.1f}+/-{w.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            win = "MQTT-SN" if m.get('PDR_mean',0)>w.get('PDR_mean',0)+1 else "WSN" if w.get('PDR_mean',0)>m.get('PDR_mean',0)+1 else "~Tie"
            print(f"  {n:<8} {nr:<6} {wp:<20} {mp:<20} {win}")
    print("\n"+"="*90+"\n")

if __name__ == "__main__":
    print("\n[MIoT] WSN vs MQTT-SN Statistical Comparison\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    if len(data) == 0: print("[ERROR] No data!"); sys.exit(1)
    plot_bars(data,1,'PDR','PDR (%)','PDR: WSN vs MQTT-SN','01_set1_pdr_bars.png')
    plot_bars(data,1,'Delay','Delay (ms)','Delay: WSN vs MQTT-SN','02_set1_delay_bars.png')
    plot_bars(data,1,'Dead','Dead Flows','Dead Flows','03_set1_dead_bars.png')
    plot_lines(data,1,'PDR','PDR (%)','PDR Scalability','04_set1_pdr_line.png')
    plot_bars(data,2,'PDR','PDR (%)','PDR: WSN vs MQTT-SN','05_set2_pdr_bars.png')
    plot_bars(data,2,'Delay','Delay (ms)','Delay: WSN vs MQTT-SN','06_set2_delay_bars.png')
    plot_bars(data,2,'Dead','Dead Flows','Dead Flows','07_set2_dead_bars.png')
    plot_lines(data,2,'PDR','PDR (%)','PDR Scalability','08_set2_pdr_line.png')
    plot_dashboard(data)
    plot_table(data)
    print_results(data)
