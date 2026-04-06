#!/usr/bin/env python3
"""
WSN vs MQTT-SN Statistical Comparison Analysis (Bilingual TR/EN)
================================================================
Reads multi-seed CSV data, computes mean+-std, generates graphs,
runs statistical tests (Welch t-test), outputs in Turkish and English.

Usage: python3 scripts/analyze_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys
from scipy import stats

matplotlib.use('Agg')

OUTPUT_DIR = "graphs/comparison"
DPI = 200
NODES = [50, 100, 150, 200]
MAX_SEEDS = 10

C_WSN = '#E74C3C'
C_MQTT = '#2E86C1'
C_WSN_L = '#F5B7B1'
C_MQTT_L = '#AED6F1'
C_HET = '#27AE60'

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

def load_set(prefix, nodes, max_seeds):
    """Load a set of experiments and return dict of results"""
    results = {}
    for n in nodes:
        key = f"{prefix}_{n}"
        runs = []
        for r in range(1, max_seeds + 1):
            path = f"experiments/statistical/{key}_r{r}.csv"
            df = load_csv(path)
            if df is not None:
                m = calc_metrics(df)
                if m: runs.append(m)
        # Fallback to comparison dir
        if len(runs) == 0:
            path = f"experiments/comparison/{key}.csv"
            df = load_csv(path)
            if df is not None:
                m = calc_metrics(df)
                if m: runs.append(m)
        if len(runs) > 0:
            results[key] = {
                'n_runs': len(runs),
                'runs_raw': runs,
                'PDR_mean': np.mean([r['PDR'] for r in runs]),
                'PDR_std': np.std([r['PDR'] for r in runs], ddof=1) if len(runs) > 1 else 0,
                'Delay_mean': np.mean([r['Delay'] for r in runs]),
                'Delay_std': np.std([r['Delay'] for r in runs], ddof=1) if len(runs) > 1 else 0,
                'Dead_mean': np.mean([r['Dead'] for r in runs]),
                'Dead_std': np.std([r['Dead'] for r in runs], ddof=1) if len(runs) > 1 else 0,
                'Throughput_mean': np.mean([r['Throughput'] for r in runs]),
            }
            print(f"[OK] {key}: {len(runs)} seeds")
    return results

def load_all():
    results = {}
    # Set 1 & 2
    for s in [1, 2]:
        for sc in ['wsn', 'mqtt']:
            r = load_set(f"exp{s}_{sc}", NODES, MAX_SEEDS)
            results.update(r)
    # Set 3: Hetero WSN no broker
    results.update(load_set("exp3_wsn_hetero", NODES, MAX_SEEDS))
    # Set 3b: Hetero WSN with broker
    results.update(load_set("exp3b_wsn_hetero_broker", NODES, MAX_SEEDS))
    return results

# ============================================================
# WELCH T-TEST
# ============================================================
def welch_ttest(data, key_a, key_b, metric='PDR'):
    a = data.get(key_a, {}).get('runs_raw', [])
    b = data.get(key_b, {}).get('runs_raw', [])
    if len(a) < 2 or len(b) < 2:
        return None
    va = [r[metric] for r in a]
    vb = [r[metric] for r in b]
    t_stat, p_val = stats.ttest_ind(va, vb, equal_var=False)
    return p_val

def sig_label(p):
    if p is None: return "N/A"
    if p < 0.001: return "***"
    if p < 0.01: return "**"
    if p < 0.05: return "*"
    return "ns"

# ============================================================
# BAR CHART (Error Bar) - Bilingual
# ============================================================
def plot_bars(data, setnum, metric, ylabel_tr, ylabel_en, title_tr, title_en, filename):
    for lang, ylabel, title in [('tr', ylabel_tr, title_tr), ('en', ylabel_en, title_en)]:
        fig, ax = plt.subplots(figsize=(9, 5))
        pf = f"exp{setnum}"
        wm = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
        ws = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
        mm = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
        ms = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
        x = np.arange(len(NODES)); w = 0.3
        lb_a = 'KAA (AODV+UDP)' if lang=='tr' else 'WSN (AODV+UDP)'
        ax.bar(x-w/2, wm, w, yerr=ws, capsize=5, label=lb_a, color=C_WSN, edgecolor='white', zorder=3, alpha=0.85)
        ax.bar(x+w/2, mm, w, yerr=ms, capsize=5, label='MQTT-SN', color=C_MQTT, edgecolor='white', zorder=3, alpha=0.85)
        mv = max(max(wm) if wm else 1, max(mm) if mm else 1)
        for i in range(len(NODES)):
            f1 = f'{wm[i]:.1f}' if metric != 'Dead' else f'{wm[i]:.0f}'
            f2 = f'{mm[i]:.1f}' if metric != 'Dead' else f'{mm[i]:.0f}'
            ax.text(x[i]-w/2, wm[i]+ws[i]+mv*0.02, f1, ha='center', fontsize=7, color=C_WSN, fontweight='bold')
            ax.text(x[i]+w/2, mm[i]+ms[i]+mv*0.02, f2, ha='center', fontsize=7, color=C_MQTT, fontweight='bold')
        ax.set_xticks(x); ax.set_xticklabels([f'{n}' for n in NODES])
        xl = 'Sensor Dugum Sayisi' if lang=='tr' else 'Number of Sensor Nodes'
        ax.set_xlabel(xl, fontsize=11); ax.set_ylabel(ylabel, fontsize=11)
        nr = data.get(f"{pf}_wsn_50", {}).get('n_runs', 1)
        seeds_label = f'{nr} tohum' if lang=='tr' else f'{nr} seeds'
        ax.set_title(f'{title} ({seeds_label}, mean+/-std)', fontsize=12, fontweight='bold')
        ax.legend(); ax.grid(axis='y', alpha=0.3, zorder=0)
        fn = filename.replace('.png', f'_{lang}.png')
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# LINE CHART (Confidence Band) - Bilingual
# ============================================================
def plot_lines(data, setnum, metric, ylabel_tr, ylabel_en, title_tr, title_en, filename):
    for lang, ylabel, title in [('tr', ylabel_tr, title_tr), ('en', ylabel_en, title_en)]:
        fig, ax = plt.subplots(figsize=(9, 5))
        pf = f"exp{setnum}"
        wm = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
        ws = [data.get(f"{pf}_wsn_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
        mm = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
        ms = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_std', 0) for n in NODES]
        lb_a = 'KAA (AODV+UDP)' if lang=='tr' else 'WSN (AODV+UDP)'
        ax.plot(NODES, wm, 'o-', color=C_WSN, linewidth=2, markersize=8, label=lb_a)
        ax.fill_between(NODES, [m-s for m,s in zip(wm,ws)], [m+s for m,s in zip(wm,ws)], color=C_WSN, alpha=0.15)
        ax.plot(NODES, mm, 's-', color=C_MQTT, linewidth=2, markersize=8, label='MQTT-SN')
        ax.fill_between(NODES, [m-s for m,s in zip(mm,ms)], [m+s for m,s in zip(mm,ms)], color=C_MQTT, alpha=0.15)
        for i in range(len(NODES)):
            ax.annotate(f'{wm[i]:.1f}', (NODES[i], wm[i]), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9, color=C_WSN)
            ax.annotate(f'{mm[i]:.1f}', (NODES[i], mm[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color=C_MQTT)
        xl = 'Sensor Dugum Sayisi' if lang=='tr' else 'Number of Sensor Nodes'
        band_label = 'golgeli alan = +/-1 std' if lang=='tr' else 'shaded area = +/-1 std'
        ax.set_xlabel(xl, fontsize=11); ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(f'{title} ({band_label})', fontsize=12, fontweight='bold')
        ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
        fn = filename.replace('.png', f'_{lang}.png')
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# DASHBOARD (5 scenarios) - Bilingual
# ============================================================
def plot_dashboard(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        t = 'KAA ile MQTT-SN Istatistiksel Karsilastirma Panosu' if lang=='tr' else 'WSN vs MQTT-SN Statistical Comparison Dashboard'
        fig.suptitle(t, fontsize=16, fontweight='bold')
        if lang == 'tr':
            scen = [
                ('exp1_wsn', 'KAA Sabit A.Yok', C_WSN, 'o-'),
                ('exp1_mqtt', 'MQTT-SN A.Yok', C_MQTT, 's-'),
                ('exp3_wsn_hetero', 'KAA Hetero A.Yok', C_HET, '^-'),
                ('exp2_wsn', 'KAA Sabit A.Var', C_WSN_L, 'o--'),
                ('exp2_mqtt', 'MQTT-SN A.Var', C_MQTT_L, 's--'),
            ]
            panels = [
                (axes[0,0], 'PDR', 'PDR (%)', 'Paket Teslim Orani'),
                (axes[0,1], 'Delay', 'Gecikme (ms)', 'Uctan Uca Gecikme'),
                (axes[1,0], 'Throughput', 'Verim (kbps)', 'Ag Verimi'),
                (axes[1,1], 'Dead', 'Basarisiz Akis', 'Basarisiz Akis Sayisi'),
            ]
        else:
            scen = [
                ('exp1_wsn', 'WSN Const. No Broker', C_WSN, 'o-'),
                ('exp1_mqtt', 'MQTT-SN No Broker', C_MQTT, 's-'),
                ('exp3_wsn_hetero', 'WSN Hetero No Broker', C_HET, '^-'),
                ('exp2_wsn', 'WSN Const. W/Broker', C_WSN_L, 'o--'),
                ('exp2_mqtt', 'MQTT-SN W/Broker', C_MQTT_L, 's--'),
            ]
            panels = [
                (axes[0,0], 'PDR', 'PDR (%)', 'Packet Delivery Ratio'),
                (axes[0,1], 'Delay', 'Delay (ms)', 'End-to-End Delay'),
                (axes[1,0], 'Throughput', 'Throughput (kbps)', 'Network Throughput'),
                (axes[1,1], 'Dead', 'Dead Flows', 'Dead Flow Count'),
            ]
        for ax, m, yl, tt in panels:
            for pf, lb, cl, st in scen:
                mn = [data.get(f"{pf}_{n}",{}).get(f'{m}_mean',0) for n in NODES]
                sd = [data.get(f"{pf}_{n}",{}).get(f'{m}_std',0) for n in NODES]
                ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, linewidth=2, markersize=6, label=lb, capsize=3)
            xl = 'Dugum Sayisi' if lang=='tr' else 'Nodes'
            ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(tt, fontweight='bold')
            ax.set_xticks(NODES); ax.legend(fontsize=6); ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'10_dashboard_{lang}.png'), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] 10_dashboard_{lang}.png")

# ============================================================
# EQUAL LOAD COMPARISON (Set 3 + Set 3b) - Bilingual
# ============================================================
def plot_equal_load(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        if lang == 'tr':
            fig.suptitle('Esit Yuk Karsilastirmasi (Araci Yok)', fontsize=13, fontweight='bold')
            labels = ['KAA Sabit (4kbps)', 'KAA Hetero (esit yuk)', 'MQTT-SN']
            xl = 'Dugum Sayisi'; yl1 = 'PDR (%)'; yl2 = 'Gecikme (ms)'
            t1 = 'PDR: Esit Yuk'; t2 = 'Gecikme: Esit Yuk'
        else:
            fig.suptitle('Equal Load Comparison (No Broker)', fontsize=13, fontweight='bold')
            labels = ['WSN Constant (4kbps)', 'WSN Hetero (equal load)', 'MQTT-SN']
            xl = 'Number of Nodes'; yl1 = 'PDR (%)'; yl2 = 'Delay (ms)'
            t1 = 'PDR: Equal Load'; t2 = 'Delay: Equal Load'

        ax = axes[0]
        for pf, lb, cl, st in [('exp1_wsn', labels[0], C_WSN, 'o-'), ('exp3_wsn_hetero', labels[1], C_HET, '^-'), ('exp1_mqtt', labels[2], C_MQTT, 's-')]:
            mn = [data.get(f"{pf}_{n}",{}).get('PDR_mean',0) for n in NODES]
            sd = [data.get(f"{pf}_{n}",{}).get('PDR_std',0) for n in NODES]
            ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, lw=2, ms=7, capsize=4, label=lb)
            for i in range(len(NODES)):
                ax.annotate(f'{mn[i]:.1f}', (NODES[i], mn[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, color=cl)
        ax.set_xlabel(xl); ax.set_ylabel(yl1); ax.set_title(t1, fontweight='bold')
        ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)

        ax = axes[1]
        for pf, lb, cl, st in [('exp1_wsn', labels[0], C_WSN, 'o-'), ('exp3_wsn_hetero', labels[1], C_HET, '^-'), ('exp1_mqtt', labels[2], C_MQTT, 's-')]:
            mn = [data.get(f"{pf}_{n}",{}).get('Delay_mean',0) for n in NODES]
            sd = [data.get(f"{pf}_{n}",{}).get('Delay_std',0) for n in NODES]
            ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, lw=2, ms=7, capsize=4, label=lb)
        ax.set_xlabel(xl); ax.set_ylabel(yl2); ax.set_title(t2, fontweight='bold')
        ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)

        fn = f'12_equal_load_{lang}.png'
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# EQUAL LOAD WITH BROKER (Set 3b vs Set 2 MQTT) - Bilingual
# ============================================================
def plot_equal_load_broker(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        if lang == 'tr':
            fig.suptitle('Esit Yuk Karsilastirmasi (Araci Var)', fontsize=13, fontweight='bold')
            labels = ['KAA Sabit+Araci', 'KAA Hetero+Araci', 'MQTT-SN+Araci']
            xl = 'Dugum Sayisi'
        else:
            fig.suptitle('Equal Load Comparison (With Broker)', fontsize=13, fontweight='bold')
            labels = ['WSN Const.+Broker', 'WSN Hetero+Broker', 'MQTT-SN+Broker']
            xl = 'Number of Nodes'

        ax = axes[0]
        for pf, lb, cl, st in [('exp2_wsn', labels[0], C_WSN, 'o-'), ('exp3b_wsn_hetero_broker', labels[1], C_HET, '^-'), ('exp2_mqtt', labels[2], C_MQTT, 's-')]:
            mn = [data.get(f"{pf}_{n}",{}).get('PDR_mean',0) for n in NODES]
            sd = [data.get(f"{pf}_{n}",{}).get('PDR_std',0) for n in NODES]
            ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, lw=2, ms=7, capsize=4, label=lb)
            for i in range(len(NODES)):
                ax.annotate(f'{mn[i]:.1f}', (NODES[i], mn[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, color=cl)
        ax.set_xlabel(xl); ax.set_ylabel('PDR (%)')
        ax.set_title('PDR' if lang=='en' else 'PDR', fontweight='bold')
        ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)

        ax = axes[1]
        for pf, lb, cl, st in [('exp2_wsn', labels[0], C_WSN, 'o-'), ('exp3b_wsn_hetero_broker', labels[1], C_HET, '^-'), ('exp2_mqtt', labels[2], C_MQTT, 's-')]:
            mn = [data.get(f"{pf}_{n}",{}).get('Delay_mean',0) for n in NODES]
            sd = [data.get(f"{pf}_{n}",{}).get('Delay_std',0) for n in NODES]
            ax.errorbar(NODES, mn, yerr=sd, fmt=st, color=cl, lw=2, ms=7, capsize=4, label=lb)
        yl = 'Gecikme (ms)' if lang=='tr' else 'Delay (ms)'
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        ax.set_title('Gecikme' if lang=='tr' else 'Delay', fontweight='bold')
        ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)

        fn = f'13_equal_load_broker_{lang}.png'
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# BROKER IMPACT - Bilingual
# ============================================================
def plot_broker_impact(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        t = 'Merkezi Toplama Dugumunun PDR Etkisi' if lang=='tr' else 'Broker Impact on PDR'
        fig.suptitle(t, fontsize=14, fontweight='bold')

        for idx, (sc, sc_label) in enumerate([('wsn', 'KAA' if lang=='tr' else 'WSN'), ('mqtt', 'MQTT-SN')]):
            ax = axes[idx]
            no = [data.get(f"exp1_{sc}_{n}", {}).get('PDR_mean', 0) for n in NODES]
            no_s = [data.get(f"exp1_{sc}_{n}", {}).get('PDR_std', 0) for n in NODES]
            yes = [data.get(f"exp2_{sc}_{n}", {}).get('PDR_mean', 0) for n in NODES]
            yes_s = [data.get(f"exp2_{sc}_{n}", {}).get('PDR_std', 0) for n in NODES]
            lb_no = 'Araci Yok' if lang=='tr' else 'No Broker'
            lb_yes = 'Araci Var' if lang=='tr' else 'With Broker'
            c1 = C_WSN if sc=='wsn' else C_MQTT
            c2 = C_WSN_L if sc=='wsn' else C_MQTT_L
            ax.errorbar(NODES, no, yerr=no_s, fmt='o-', color=c1, lw=2, ms=8, capsize=4, label=f'{sc_label} {lb_no}')
            ax.errorbar(NODES, yes, yerr=yes_s, fmt='o--', color=c2, lw=2, ms=8, capsize=4, label=f'{sc_label} {lb_yes}')
            for i in range(len(NODES)):
                ax.annotate(f'{no[i]:.1f}%', (NODES[i], no[i]), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9)
                ax.annotate(f'{yes[i]:.1f}%', (NODES[i], yes[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9)
            xl = 'Dugum Sayisi' if lang=='tr' else 'Nodes'
            ax.set_xlabel(xl); ax.set_ylabel('PDR (%)')
            ax.set_title(f'{sc_label}: Broker Impact' if lang=='en' else f'{sc_label}: Araci Etkisi', fontweight='bold')
            ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)

        fn = f'09_broker_impact_{lang}.png'
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# PRINT RESULTS - Bilingual with p-values
# ============================================================
def print_results(data):
    for lang in ['tr', 'en']:
        if lang == 'tr':
            print("\n" + "="*120)
            print("  KAA ile MQTT-SN ISTATISTIKSEL KARSILASTIRMA (TURKCE)")
            print("="*120)
        else:
            print("\n" + "="*120)
            print("  WSN vs MQTT-SN STATISTICAL COMPARISON (ENGLISH)")
            print("="*120)

        for s in [1,2]:
            if lang == 'tr':
                sn = "ARACI YOK" if s==1 else "ARACI VAR"
                print(f"\n  --- KUME {s}: {sn} ---")
                print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA PDR':<20} {'MQTT PDR':<20} {'p(PDR)':<8} {'KAA Gecikme':<20} {'MQTT Gecikme':<20} {'p(Del)':<8}")
            else:
                sn = "NO BROKER" if s==1 else "WITH BROKER"
                print(f"\n  --- SET {s}: {sn} ---")
                print(f"  {'Nodes':<8} {'Seeds':<6} {'WSN PDR':<20} {'MQTT PDR':<20} {'p(PDR)':<8} {'WSN Delay':<20} {'MQTT Delay':<20} {'p(Del)':<8}")
            print("  "+"-"*110)
            for n in NODES:
                w = data.get(f"exp{s}_wsn_{n}",{}); m = data.get(f"exp{s}_mqtt_{n}",{})
                nr = w.get('n_runs',0)
                wp = f"{w.get('PDR_mean',0):.1f}+/-{w.get('PDR_std',0):.1f}%"
                mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
                wd = f"{w.get('Delay_mean',0):.1f}+/-{w.get('Delay_std',0):.1f}ms"
                md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
                p_pdr = welch_ttest(data, f"exp{s}_wsn_{n}", f"exp{s}_mqtt_{n}", 'PDR')
                p_del = welch_ttest(data, f"exp{s}_wsn_{n}", f"exp{s}_mqtt_{n}", 'Delay')
                pp = f"{p_pdr:.4f}" if p_pdr is not None else "N/A"
                pd = f"{p_del:.4f}" if p_del is not None else "N/A"
                print(f"  {n:<8} {nr:<6} {wp:<20} {mp:<20} {pp:<8} {wd:<20} {md:<20} {pd:<8}")

        # Set 3: Equal load no broker
        if lang == 'tr':
            print(f"\n  --- KUME 3: ESIT YUK, ARACI YOK (KAA Hetero vs MQTT-SN) ---")
            print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA Het. PDR':<22} {'MQTT-SN PDR':<22} {'p(PDR)':<8} {'KAA Het. Gec.':<22} {'MQTT-SN Gec.':<22}")
        else:
            print(f"\n  --- SET 3: EQUAL LOAD, NO BROKER (WSN Hetero vs MQTT-SN) ---")
            print(f"  {'Nodes':<8} {'Seeds':<6} {'WSN Het. PDR':<22} {'MQTT-SN PDR':<22} {'p(PDR)':<8} {'WSN Het. Delay':<22} {'MQTT-SN Delay':<22}")
        print("  "+"-"*110)
        for n in NODES:
            h = data.get(f"exp3_wsn_hetero_{n}",{}); m = data.get(f"exp1_mqtt_{n}",{})
            nr = h.get('n_runs',0)
            hp = f"{h.get('PDR_mean',0):.1f}+/-{h.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            hd = f"{h.get('Delay_mean',0):.1f}+/-{h.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            p_pdr = welch_ttest(data, f"exp3_wsn_hetero_{n}", f"exp1_mqtt_{n}", 'PDR')
            pp = f"{p_pdr:.4f}" if p_pdr is not None else "N/A"
            print(f"  {n:<8} {nr:<6} {hp:<22} {mp:<22} {pp:<8} {hd:<22} {md:<22}")

        # Set 3b: Equal load with broker
        if lang == 'tr':
            print(f"\n  --- KUME 3b: ESIT YUK, ARACI VAR (KAA Het.+Araci vs MQTT-SN+Araci) ---")
            print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA Het.+A PDR':<22} {'MQTT+A PDR':<22} {'p(PDR)':<8} {'KAA Het.+A Gec.':<22} {'MQTT+A Gec.':<22}")
        else:
            print(f"\n  --- SET 3b: EQUAL LOAD, WITH BROKER (WSN Het.+Broker vs MQTT-SN+Broker) ---")
            print(f"  {'Nodes':<8} {'Seeds':<6} {'WSN Het.+B PDR':<22} {'MQTT+B PDR':<22} {'p(PDR)':<8} {'WSN Het.+B Del.':<22} {'MQTT+B Del.':<22}")
        print("  "+"-"*110)
        for n in NODES:
            h = data.get(f"exp3b_wsn_hetero_broker_{n}",{}); m = data.get(f"exp2_mqtt_{n}",{})
            nr = h.get('n_runs',0)
            hp = f"{h.get('PDR_mean',0):.1f}+/-{h.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            hd = f"{h.get('Delay_mean',0):.1f}+/-{h.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            p_pdr = welch_ttest(data, f"exp3b_wsn_hetero_broker_{n}", f"exp2_mqtt_{n}", 'PDR')
            pp = f"{p_pdr:.4f}" if p_pdr is not None else "N/A"
            print(f"  {n:<8} {nr:<6} {hp:<22} {mp:<22} {pp:<8} {hd:<22} {md:<22}")

        print("\n"+"="*120+"\n")

# ============================================================
if __name__ == "__main__":
    print("\n[MIoT] WSN vs MQTT-SN Statistical Comparison Analysis\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_all()
    if len(data) == 0: print("[ERROR] No data found!"); sys.exit(1)

    # Set 1: No Broker
    plot_bars(data, 1, 'PDR', 'PDR (%)', 'PDR (%)',
             'Paket Teslim Orani: KAA ve MQTT-SN - Araci Yok',
             'PDR: WSN vs MQTT-SN - No Broker', '01_set1_pdr_bar.png')
    plot_bars(data, 1, 'Delay', 'Gecikme (ms)', 'Delay (ms)',
             'Gecikme: KAA ve MQTT-SN - Araci Yok',
             'Delay: WSN vs MQTT-SN - No Broker', '02_set1_delay_bar.png')
    plot_lines(data, 1, 'PDR', 'PDR (%)', 'PDR (%)',
              'PDR Olceklenebilirligi - Araci Yok',
              'PDR Scalability - No Broker', '04_set1_pdr_line.png')
    plot_lines(data, 1, 'Delay', 'Gecikme (ms)', 'Delay (ms)',
              'Gecikme Olceklenebilirligi - Araci Yok',
              'Delay Scalability - No Broker', '04b_set1_delay_line.png')

    # Set 2: With Broker
    plot_bars(data, 2, 'PDR', 'PDR (%)', 'PDR (%)',
             'Paket Teslim Orani: KAA ve MQTT-SN - Araci Var',
             'PDR: WSN vs MQTT-SN - With Broker', '05_set2_pdr_bar.png')
    plot_bars(data, 2, 'Delay', 'Gecikme (ms)', 'Delay (ms)',
             'Gecikme: KAA ve MQTT-SN - Araci Var',
             'Delay: WSN vs MQTT-SN - With Broker', '06_set2_delay_bar.png')
    plot_lines(data, 2, 'PDR', 'PDR (%)', 'PDR (%)',
              'PDR Olceklenebilirligi - Araci Var',
              'PDR Scalability - With Broker', '08_set2_pdr_line.png')
    plot_lines(data, 2, 'Delay', 'Gecikme (ms)', 'Delay (ms)',
              'Gecikme Olceklenebilirligi - Araci Var',
              'Delay Scalability - With Broker', '08b_set2_delay_line.png')

    # Comparisons
    plot_broker_impact(data)
    plot_dashboard(data)
    plot_equal_load(data)
    plot_equal_load_broker(data)

    print_results(data)
