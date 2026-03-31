#!/usr/bin/env python3
"""
KAA vs MQTT-SN Istatistiksel Karsilastirma Analizi (Turkce)
=============================================================
Coklu tohum verilerini okur, ort+-std hesaplar, Turkce grafikler uretir

Kullanim: python3 scripts/analyze_comparison.py
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
MAX_SEEDS = 10

C_WSN = '#E74C3C'
C_MQTT = '#2E86C1'
C_WSN_L = '#F5B7B1'
C_MQTT_L = '#AED6F1'

def load_csv(path):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if 'TxPackets' in df.columns:
                return df
        except Exception:
            pass
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
                    print(f"[OK] {key}: {len(runs)} tohum")

    # Set 3: Hetero WSN (esit yuk)
    for n in NODES:
        key = f"exp3_wsn_hetero_{n}"
        runs = []
        for r in range(1, MAX_SEEDS + 1):
            path = f"experiments/statistical/{key}_r{r}.csv"
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
            print(f"[OK] {key}: {len(runs)} tohum")

    return results

# ============================================================
# CUBUK GRAFIK (Error Bar)
# ============================================================
def plot_bars(data, setnum, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    pf = f"exp{setnum}"
    wm = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ws = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    mm = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ms = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    x = np.arange(len(NODES)); w = 0.3
    ax.bar(x-w/2, wm, w, yerr=ws, capsize=5, label='KAA (AODV+UDP)', color=C_WSN, edgecolor='white', zorder=3, alpha=0.85)
    ax.bar(x+w/2, mm, w, yerr=ms, capsize=5, label='MQTT-SN', color=C_MQTT, edgecolor='white', zorder=3, alpha=0.85)
    mv = max(max(wm) if wm else 1, max(mm) if mm else 1)
    for i in range(len(NODES)):
        f1 = f'{wm[i]:.1f}' if metric != 'Dead' else f'{wm[i]:.0f}'
        f2 = f'{mm[i]:.1f}' if metric != 'Dead' else f'{mm[i]:.0f}'
        ax.text(x[i]-w/2, wm[i]+ws[i]+mv*0.02, f1, ha='center', fontsize=7, color=C_WSN, fontweight='bold')
        ax.text(x[i]+w/2, mm[i]+ms[i]+mv*0.02, f2, ha='center', fontsize=7, color=C_MQTT, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels([f'{n}' for n in NODES])
    ax.set_xlabel('Sensor Dugum Sayisi', fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    sn = "Araci Yok" if setnum == 1 else "Araci Var"
    nr = data.get(f"{pf}_wsn_50", {}).get('n_runs', 1)
    ax.set_title(f'{title} - {sn} ({nr} tohum, ort.+/-std)', fontsize=12, fontweight='bold')
    ax.legend(); ax.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight'); plt.close()
    print(f"[OK] {filename}")

# ============================================================
# CIZGI GRAFIK (Guven Bandi)
# ============================================================
def plot_lines(data, setnum, metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5))
    pf = f"exp{setnum}"
    wm = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ws = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    mm = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
    ms = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
    ax.plot(NODES, wm, 'o-', color=C_WSN, linewidth=2, markersize=8, label='KAA (AODV+UDP)')
    ax.fill_between(NODES, [m-s for m,s in zip(wm,ws)], [m+s for m,s in zip(wm,ws)], color=C_WSN, alpha=0.15)
    ax.plot(NODES, mm, 's-', color=C_MQTT, linewidth=2, markersize=8, label='MQTT-SN')
    ax.fill_between(NODES, [m-s for m,s in zip(mm,ms)], [m+s for m,s in zip(mm,ms)], color=C_MQTT, alpha=0.15)
    for i in range(len(NODES)):
        ax.annotate(f'{wm[i]:.1f}', (NODES[i], wm[i]), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9, color=C_WSN)
        ax.annotate(f'{mm[i]:.1f}', (NODES[i], mm[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color=C_MQTT)
    ax.set_xlabel('Sensor Dugum Sayisi', fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    sn = "Araci Yok" if setnum == 1 else "Araci Var"
    ax.set_title(f'{title} - {sn} (golgeli alan = +/-1 std)', fontsize=12, fontweight='bold')
    ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=DPI, bbox_inches='tight'); plt.close()
    print(f"[OK] {filename}")

# ============================================================
# ANA PANO (4 panel, error bar)
# ============================================================
def plot_dashboard(data):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('KAA ile MQTT-SN Istatistiksel Karsilastirma Panosu', fontsize=16, fontweight='bold')
    scen = [
        ('exp1_wsn', 'KAA Sabit A.Yok', C_WSN, 'o-'),
        ('exp1_mqtt', 'MQTT-SN A.Yok', C_MQTT, 's-'),
        ('exp3_wsn_hetero', 'KAA Hetero A.Yok', '#27AE60', '^-'),
        ('exp2_wsn', 'KAA Sabit A.Var', C_WSN_L, 'o--'),
        ('exp2_mqtt', 'MQTT-SN A.Var', C_MQTT_L, 's--'),
    ]
    panels = [
        (axes[0,0], 'PDR', 'PDR (%)', 'Paket Teslim Orani'),
        (axes[0,1], 'Delay', 'Gecikme (ms)', 'Uctan Uca Gecikme'),
        (axes[1,0], 'Throughput', 'Verim (kbps)', 'Ag Verimi'),
        (axes[1,1], 'Dead', 'Basarisiz Akis', 'Basarisiz Akis Sayisi'),
    ]
    for ax, m, yl, t in panels:
        for pf, lb, cl, st in scen:
            mn = [data.get(f"{pf}_{n}",{}).get(f'{m}_mean',0) for n in NODES]
            sd = [data.get(f"{pf}_{n}",{}).get(f'{m}_std',0) for n in NODES]
            ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, linewidth=2, markersize=6, label=lb, capsize=3)
        ax.set_xlabel('Dugum Sayisi'); ax.set_ylabel(yl)
        ax.set_title(t, fontweight='bold')
        ax.set_xticks(NODES); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '10_ana_pano.png'), dpi=DPI, bbox_inches='tight'); plt.close()
    print("[OK] 10_ana_pano.png")

# ============================================================
# OZET TABLO
# ============================================================
def plot_table(data):
    fig, ax = plt.subplots(figsize=(18, 11)); ax.axis('off')
    hd = ['Kume','Dugum','Tohum','KAA PDR','MQTT PDR','KAA Gecikme','MQTT Gecikme','Kazanan']
    rows = []
    for s in [1,2]:
        sn = "Araci Yok" if s==1 else "Araci Var"
        for n in NODES:
            w = data.get(f"exp{s}_wsn_{n}",{}); m = data.get(f"exp{s}_mqtt_{n}",{})
            nr = w.get('n_runs',0)
            wp = f"{w.get('PDR_mean',0):.1f}+/-{w.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            wd = f"{w.get('Delay_mean',0):.1f}+/-{w.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            win = "MQTT-SN" if m.get('PDR_mean',0) > w.get('PDR_mean',0)+1 else "KAA" if w.get('PDR_mean',0)>m.get('PDR_mean',0)+1 else "~Esit"
            rows.append([sn,str(n),str(nr),wp,mp,wd,md,win])
    # Set 3: Hetero WSN vs MQTT-SN
    for n in NODES:
        h = data.get(f"exp3_wsn_hetero_{n}",{}); m = data.get(f"exp1_mqtt_{n}",{})
        nr = h.get('n_runs',0)
        hp = f"{h.get('PDR_mean',0):.1f}+/-{h.get('PDR_std',0):.1f}%"
        mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
        hd2 = f"{h.get('Delay_mean',0):.1f}+/-{h.get('Delay_std',0):.1f}ms"
        md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
        win = "MQTT-SN" if m.get('PDR_mean',0) > h.get('PDR_mean',0)+1 else "KAA Het." if h.get('PDR_mean',0)>m.get('PDR_mean',0)+1 else "~Esit"
        rows.append(["Esit Yuk",str(n),str(nr),hp,mp,hd2,md,win])
    tb = ax.table(cellText=rows, colLabels=hd, loc='center', cellLoc='center')
    tb.auto_set_font_size(False); tb.set_fontsize(8); tb.scale(1, 1.6)
    for j in range(len(hd)):
        tb[0,j].set_facecolor('#2C3E50'); tb[0,j].set_text_props(color='white', fontweight='bold')
    for i in range(1,len(rows)+1):
        if rows[i-1][-1]=="MQTT-SN":
            for j in range(len(hd)): tb[i,j].set_facecolor('#D6EAF8')
        elif "KAA" in rows[i-1][-1]:
            for j in range(len(hd)): tb[i,j].set_facecolor('#FADBD8')
    ax.set_title('Istatistiksel Ozet Tablosu (ort. +/- std)\nMavi=MQTT-SN ustun, Kirmizi=KAA ustun', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11_ozet_tablo.png'), dpi=DPI, bbox_inches='tight'); plt.close()
    print("[OK] 11_ozet_tablo.png")

# ============================================================
# ARACI ETKISI
# ============================================================
def plot_broker_impact(data):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Merkezi Toplama Dugumunun PDR Uzerindeki Etkisi', fontsize=14, fontweight='bold')

    ax = axes[0]
    wsn_no = [data.get(f"exp1_wsn_{n}", {}).get('PDR_mean', 0) for n in NODES]
    wsn_yes = [data.get(f"exp2_wsn_{n}", {}).get('PDR_mean', 0) for n in NODES]
    wsn_no_s = [data.get(f"exp1_wsn_{n}", {}).get('PDR_std', 0) for n in NODES]
    wsn_yes_s = [data.get(f"exp2_wsn_{n}", {}).get('PDR_std', 0) for n in NODES]
    ax.errorbar(NODES, wsn_no, yerr=wsn_no_s, fmt='o-', color=C_WSN, lw=2, ms=8, capsize=4, label='KAA Araci Yok')
    ax.errorbar(NODES, wsn_yes, yerr=wsn_yes_s, fmt='o--', color=C_WSN_L, lw=2, ms=8, capsize=4, label='KAA Araci Var')
    for i in range(len(NODES)):
        ax.annotate(f'{wsn_no[i]:.1f}%', (NODES[i], wsn_no[i]), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9)
        ax.annotate(f'{wsn_yes[i]:.1f}%', (NODES[i], wsn_yes[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9)
    ax.set_xlabel('Dugum Sayisi'); ax.set_ylabel('PDR (%)')
    ax.set_title('KAA: Araci Etkisi', fontweight='bold')
    ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)

    ax = axes[1]
    mqtt_no = [data.get(f"exp1_mqtt_{n}", {}).get('PDR_mean', 0) for n in NODES]
    mqtt_yes = [data.get(f"exp2_mqtt_{n}", {}).get('PDR_mean', 0) for n in NODES]
    mqtt_no_s = [data.get(f"exp1_mqtt_{n}", {}).get('PDR_std', 0) for n in NODES]
    mqtt_yes_s = [data.get(f"exp2_mqtt_{n}", {}).get('PDR_std', 0) for n in NODES]
    ax.errorbar(NODES, mqtt_no, yerr=mqtt_no_s, fmt='s-', color=C_MQTT, lw=2, ms=8, capsize=4, label='MQTT-SN Araci Yok')
    ax.errorbar(NODES, mqtt_yes, yerr=mqtt_yes_s, fmt='s--', color=C_MQTT_L, lw=2, ms=8, capsize=4, label='MQTT-SN Araci Var')
    for i in range(len(NODES)):
        ax.annotate(f'{mqtt_no[i]:.1f}%', (NODES[i], mqtt_no[i]), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9)
        ax.annotate(f'{mqtt_yes[i]:.1f}%', (NODES[i], mqtt_yes[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9)
    ax.set_xlabel('Dugum Sayisi'); ax.set_ylabel('PDR (%)')
    ax.set_title('MQTT-SN: Araci Etkisi', fontweight='bold')
    ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '09_araci_etkisi.png'), dpi=DPI, bbox_inches='tight'); plt.close()
    print("[OK] 09_araci_etkisi.png")

# ============================================================
# ESIT YUK KARSILASTIRMA (Set 1 KAA vs Set 3 Hetero KAA vs Set 1 MQTT-SN)
# ============================================================
def plot_equal_load(data):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Esit Yuk Karsilastirmasi: KAA Sabit vs KAA Hetero vs MQTT-SN', fontsize=13, fontweight='bold')

    C_HET = '#27AE60'  # green for hetero WSN

    # PDR
    ax = axes[0]
    wsn_s = [data.get(f"exp1_wsn_{n}", {}).get('PDR_mean', 0) for n in NODES]
    wsn_s_e = [data.get(f"exp1_wsn_{n}", {}).get('PDR_std', 0) for n in NODES]
    wsn_h = [data.get(f"exp3_wsn_hetero_{n}", {}).get('PDR_mean', 0) for n in NODES]
    wsn_h_e = [data.get(f"exp3_wsn_hetero_{n}", {}).get('PDR_std', 0) for n in NODES]
    mqtt = [data.get(f"exp1_mqtt_{n}", {}).get('PDR_mean', 0) for n in NODES]
    mqtt_e = [data.get(f"exp1_mqtt_{n}", {}).get('PDR_std', 0) for n in NODES]

    ax.errorbar(NODES, wsn_s, yerr=wsn_s_e, fmt='o-', color=C_WSN, lw=2, ms=7, capsize=4, label='KAA Sabit (4kbps)')
    ax.errorbar(NODES, wsn_h, yerr=wsn_h_e, fmt='^-', color=C_HET, lw=2, ms=7, capsize=4, label='KAA Hetero (esit yuk)')
    ax.errorbar(NODES, mqtt, yerr=mqtt_e, fmt='s-', color=C_MQTT, lw=2, ms=7, capsize=4, label='MQTT-SN')
    for i in range(len(NODES)):
        ax.annotate(f'{wsn_s[i]:.1f}', (NODES[i], wsn_s[i]), textcoords="offset points", xytext=(-15,10), ha='center', fontsize=8, color=C_WSN)
        ax.annotate(f'{wsn_h[i]:.1f}', (NODES[i], wsn_h[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=8, color=C_HET)
        ax.annotate(f'{mqtt[i]:.1f}', (NODES[i], mqtt[i]), textcoords="offset points", xytext=(15,10), ha='center', fontsize=8, color=C_MQTT)
    ax.set_xlabel('Dugum Sayisi'); ax.set_ylabel('PDR (%)')
    ax.set_title('PDR: Esit Yuk Altinda', fontweight='bold')
    ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Gecikme
    ax = axes[1]
    wsn_s_d = [data.get(f"exp1_wsn_{n}", {}).get('Delay_mean', 0) for n in NODES]
    wsn_s_de = [data.get(f"exp1_wsn_{n}", {}).get('Delay_std', 0) for n in NODES]
    wsn_h_d = [data.get(f"exp3_wsn_hetero_{n}", {}).get('Delay_mean', 0) for n in NODES]
    wsn_h_de = [data.get(f"exp3_wsn_hetero_{n}", {}).get('Delay_std', 0) for n in NODES]
    mqtt_d = [data.get(f"exp1_mqtt_{n}", {}).get('Delay_mean', 0) for n in NODES]
    mqtt_de = [data.get(f"exp1_mqtt_{n}", {}).get('Delay_std', 0) for n in NODES]

    ax.errorbar(NODES, wsn_s_d, yerr=wsn_s_de, fmt='o-', color=C_WSN, lw=2, ms=7, capsize=4, label='KAA Sabit')
    ax.errorbar(NODES, wsn_h_d, yerr=wsn_h_de, fmt='^-', color=C_HET, lw=2, ms=7, capsize=4, label='KAA Hetero')
    ax.errorbar(NODES, mqtt_d, yerr=mqtt_de, fmt='s-', color=C_MQTT, lw=2, ms=7, capsize=4, label='MQTT-SN')
    ax.set_xlabel('Dugum Sayisi'); ax.set_ylabel('Gecikme (ms)')
    ax.set_title('Gecikme: Esit Yuk Altinda', fontweight='bold')
    ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '12_esit_yuk_karsilastirma.png'), dpi=DPI, bbox_inches='tight'); plt.close()
    print("[OK] 12_esit_yuk_karsilastirma.png")

# ============================================================
# SONUCLARI YAZDIR
# ============================================================
def print_results(data):
    print("\n" + "="*100)
    print("  KAA ile MQTT-SN ISTATISTIKSEL KARSILASTIRMA")
    print("="*100)
    for s in [1,2]:
        sn = "ARACI YOK" if s==1 else "ARACI VAR"
        print(f"\n  --- KUME {s}: {sn} ---")
        print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA PDR':<20} {'MQTT PDR':<20} {'KAA Gecikme':<20} {'MQTT Gecikme':<20}")
        print("  "+"-"*94)
        for n in NODES:
            w = data.get(f"exp{s}_wsn_{n}",{}); m = data.get(f"exp{s}_mqtt_{n}",{})
            nr = w.get('n_runs',0)
            wp = f"{w.get('PDR_mean',0):.1f}+/-{w.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            wd = f"{w.get('Delay_mean',0):.1f}+/-{w.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            print(f"  {n:<8} {nr:<6} {wp:<20} {mp:<20} {wd:<20} {md:<20}")

    print(f"\n  --- KUME 3: ESIT YUK (KAA Hetero vs MQTT-SN) ---")
    print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA Hetero PDR':<22} {'MQTT-SN PDR':<22} {'KAA Het. Gecikme':<22} {'MQTT-SN Gecikme':<22}")
    print("  "+"-"*100)
    for n in NODES:
        h = data.get(f"exp3_wsn_hetero_{n}",{}); m = data.get(f"exp1_mqtt_{n}",{})
        nr = h.get('n_runs',0)
        hp = f"{h.get('PDR_mean',0):.1f}+/-{h.get('PDR_std',0):.1f}%"
        mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
        hd = f"{h.get('Delay_mean',0):.1f}+/-{h.get('Delay_std',0):.1f}ms"
        md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
        print(f"  {n:<8} {nr:<6} {hp:<22} {mp:<22} {hd:<22} {md:<22}")

    print("\n"+"="*100+"\n")

# ============================================================
if __name__ == "__main__":
    print("\n[TIoT] KAA ile MQTT-SN Istatistiksel Karsilastirma Analizi\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    if len(data) == 0: print("[HATA] Veri bulunamadi!"); sys.exit(1)

    # Kume 1: Araci Yok
    plot_bars(data, 1, 'PDR', 'PDR (%)', 'Paket Teslim Orani: KAA ve MQTT-SN', '01_set1_pdr_cubuk.png')
    plot_bars(data, 1, 'Delay', 'Gecikme (ms)', 'Gecikme: KAA ve MQTT-SN', '02_set1_gecikme_cubuk.png')
    plot_bars(data, 1, 'Dead', 'Basarisiz Akis', 'Basarisiz Akis Sayisi', '03_set1_basarisiz_cubuk.png')
    plot_lines(data, 1, 'PDR', 'PDR (%)', 'PDR Olceklenebilirligi', '04_set1_pdr_cizgi.png')
    plot_lines(data, 1, 'Delay', 'Gecikme (ms)', 'Gecikme Olceklenebilirligi', '04b_set1_gecikme_cizgi.png')

    # Kume 2: Araci Var
    plot_bars(data, 2, 'PDR', 'PDR (%)', 'Paket Teslim Orani: KAA ve MQTT-SN', '05_set2_pdr_cubuk.png')
    plot_bars(data, 2, 'Delay', 'Gecikme (ms)', 'Gecikme: KAA ve MQTT-SN', '06_set2_gecikme_cubuk.png')
    plot_bars(data, 2, 'Dead', 'Basarisiz Akis', 'Basarisiz Akis Sayisi', '07_set2_basarisiz_cubuk.png')
    plot_lines(data, 2, 'PDR', 'PDR (%)', 'PDR Olceklenebilirligi', '08_set2_pdr_cizgi.png')
    plot_lines(data, 2, 'Delay', 'Gecikme (ms)', 'Gecikme Olceklenebilirligi', '08b_set2_gecikme_cizgi.png')

    # Karsilastirma
    plot_broker_impact(data)
    plot_dashboard(data)
    plot_table(data)
    plot_equal_load(data)

    print_results(data)
