#!/usr/bin/env python3
"""
WSN vs MQTT-SN Statistical Comparison Analysis (Bilingual TR/EN)
+ Multi-Broker Hierarchy Sweep (Direction 1)
================================================================
Usage: python3 scripts/analyze_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os, sys
from scipy import stats

matplotlib.use('Agg')

OUTPUT_DIR      = "graphs/comparison"
OUTPUT_DIR_HIER = "graphs/hier"
DPI             = 200
NODES           = [50, 100, 150, 200]
LB_VALUES       = [1, 2, 4, 5]   # numLocalBrokers sweep values
MAX_SEEDS       = 10

C_WSN   = '#E74C3C'
C_MQTT  = '#2E86C1'
C_WSN_L = '#F5B7B1'
C_MQTT_L= '#AED6F1'
C_HET   = '#27AE60'
# Hierarchy colors — one per LB value
C_HIER  = {1: '#E67E22', 2: '#8E44AD', 4: '#16A085', 5: '#2C3E50'}

# ============================================================
# DATA LOADING
# ============================================================
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
    d  = df['AvgDelay_ms'][df['AvgDelay_ms'] > 0]
    return {
        'PDR':        rx/tx*100 if tx > 0 else 0,
        'Delay':      d.mean() if len(d) > 0 else 0,
        'Throughput': df['Throughput_kbps'].mean(),
        'Dead':       len(df[df['RxPackets'] == 0]),
    }

def load_set(prefix, nodes, max_seeds, base_dir="experiments/statistical"):
    results = {}
    for n in nodes:
        key  = f"{prefix}_{n}"
        runs = []
        for r in range(1, max_seeds + 1):
            path = f"{base_dir}/{key}_r{r}.csv"
            df   = load_csv(path)
            if df is not None:
                m = calc_metrics(df)
                if m: runs.append(m)
        # Fallback
        if len(runs) == 0:
            path = f"experiments/comparison/{key}.csv"
            df   = load_csv(path)
            if df is not None:
                m = calc_metrics(df)
                if m: runs.append(m)
        if len(runs) > 0:
            results[key] = {
                'n_runs':          len(runs),
                'runs_raw':        runs,
                'PDR_mean':        np.mean([r['PDR'] for r in runs]),
                'PDR_std':         np.std ([r['PDR'] for r in runs], ddof=1) if len(runs)>1 else 0,
                'Delay_mean':      np.mean([r['Delay'] for r in runs]),
                'Delay_std':       np.std ([r['Delay'] for r in runs], ddof=1) if len(runs)>1 else 0,
                'Dead_mean':       np.mean([r['Dead'] for r in runs]),
                'Dead_std':        np.std ([r['Dead'] for r in runs], ddof=1) if len(runs)>1 else 0,
                'Throughput_mean': np.mean([r['Throughput'] for r in runs]),
            }
            print(f"[OK] {key}: {len(runs)} seeds")
    return results

def load_hier_set(lb_values, node=200, max_seeds=MAX_SEEDS):
    """Load multi-broker hierarchy experiments.
    Returns dict keyed by 'hier_lb{LB}_{node}'.
    """
    results = {}
    for lb in lb_values:
        key  = f"hier_lb{lb}_{node}"
        runs = []
        for r in range(1, max_seeds + 1):
            path = f"experiments/hier/exp_hier_lb{lb}_{node}_r{r}.csv"
            df   = load_csv(path)
            if df is not None:
                m = calc_metrics(df)
                if m: runs.append(m)
        if len(runs) > 0:
            results[key] = {
                'n_runs':          len(runs),
                'runs_raw':        runs,
                'PDR_mean':        np.mean([r['PDR'] for r in runs]),
                'PDR_std':         np.std ([r['PDR'] for r in runs], ddof=1) if len(runs)>1 else 0,
                'Delay_mean':      np.mean([r['Delay'] for r in runs]),
                'Delay_std':       np.std ([r['Delay'] for r in runs], ddof=1) if len(runs)>1 else 0,
                'lb':              lb,
            }
            print(f"[OK] {key}: {len(runs)} seeds")
    return results

def load_all():
    results = {}
    for s in [1, 2]:
        for sc in ['wsn', 'mqtt']:
            results.update(load_set(f"exp{s}_{sc}", NODES, MAX_SEEDS))
    results.update(load_set("exp3_wsn_hetero",        NODES, MAX_SEEDS))
    results.update(load_set("exp3b_wsn_hetero_broker", NODES, MAX_SEEDS))
    return results

# ============================================================
# STATISTICS
# ============================================================
def welch_ttest(data, key_a, key_b, metric='PDR'):
    a = data.get(key_a, {}).get('runs_raw', [])
    b = data.get(key_b, {}).get('runs_raw', [])
    if len(a) < 2 or len(b) < 2: return None
    va = [r[metric] for r in a]
    vb = [r[metric] for r in b]
    _, p = stats.ttest_ind(va, vb, equal_var=False)
    return p

def sig_label(p):
    if p is None:   return "N/A"
    if p < 0.001:   return "***"
    if p < 0.01:    return "**"
    if p < 0.05:    return "*"
    return "ns"

# ============================================================
# BAR CHART
# ============================================================
def plot_bars(data, setnum, metric, ylabel_tr, ylabel_en, title_tr, title_en, filename):
    for lang, ylabel, title in [('tr', ylabel_tr, title_tr), ('en', ylabel_en, title_en)]:
        fig, ax = plt.subplots(figsize=(9, 5))
        pf = f"exp{setnum}"
        wm = [data.get(f"{pf}_wsn_{n}",  {}).get(f'{metric}_mean', 0) for n in NODES]
        ws = [data.get(f"{pf}_wsn_{n}",  {}).get(f'{metric}_std',  0) for n in NODES]
        mm = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
        ms = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_std',  0) for n in NODES]
        x = np.arange(len(NODES)); w = 0.3
        lb_a = 'KAA (AODV+UDP)' if lang=='tr' else 'WSN (AODV+UDP)'
        ax.bar(x-w/2, wm, w, yerr=ws, capsize=5, label=lb_a,    color=C_WSN,  edgecolor='white', zorder=3, alpha=0.85)
        ax.bar(x+w/2, mm, w, yerr=ms, capsize=5, label='MQTT-SN', color=C_MQTT, edgecolor='white', zorder=3, alpha=0.85)
        mv = max(max(wm) if wm else 1, max(mm) if mm else 1)
        for i in range(len(NODES)):
            f1 = f'{wm[i]:.1f}' if metric!='Dead' else f'{wm[i]:.0f}'
            f2 = f'{mm[i]:.1f}' if metric!='Dead' else f'{mm[i]:.0f}'
            ax.text(x[i]-w/2, wm[i]+ws[i]+mv*0.02, f1, ha='center', fontsize=7, color=C_WSN,  fontweight='bold')
            ax.text(x[i]+w/2, mm[i]+ms[i]+mv*0.02, f2, ha='center', fontsize=7, color=C_MQTT, fontweight='bold')
        ax.set_xticks(x); ax.set_xticklabels([f'{n}' for n in NODES])
        xl  = 'Sensor Dugum Sayisi' if lang=='tr' else 'Number of Sensor Nodes'
        nr  = data.get(f"{pf}_wsn_50", {}).get('n_runs', 1)
        slb = f'{nr} tohum' if lang=='tr' else f'{nr} seeds'
        ax.set_xlabel(xl, fontsize=11); ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(f'{title} ({slb}, mean+/-std)', fontsize=12, fontweight='bold')
        ax.legend(); ax.grid(axis='y', alpha=0.3, zorder=0)
        fn = filename.replace('.png', f'_{lang}.png')
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# LINE CHART
# ============================================================
def plot_lines(data, setnum, metric, ylabel_tr, ylabel_en, title_tr, title_en, filename):
    for lang, ylabel, title in [('tr', ylabel_tr, title_tr), ('en', ylabel_en, title_en)]:
        fig, ax = plt.subplots(figsize=(9, 5))
        pf = f"exp{setnum}"
        wm = [data.get(f"{pf}_wsn_{n}",  {}).get(f'{metric}_mean', 0) for n in NODES]
        ws = [data.get(f"{pf}_wsn_{n}",  {}).get(f'{metric}_std',  0) for n in NODES]
        mm = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_mean', 0) for n in NODES]
        ms = [data.get(f"{pf}_mqtt_{n}", {}).get(f'{metric}_std',  0) for n in NODES]
        lb_a = 'KAA (AODV+UDP)' if lang=='tr' else 'WSN (AODV+UDP)'
        ax.plot(NODES, wm, 'o-', color=C_WSN,  linewidth=2, markersize=8, label=lb_a)
        ax.fill_between(NODES, [m-s for m,s in zip(wm,ws)], [m+s for m,s in zip(wm,ws)], color=C_WSN,  alpha=0.15)
        ax.plot(NODES, mm, 's-', color=C_MQTT, linewidth=2, markersize=8, label='MQTT-SN')
        ax.fill_between(NODES, [m-s for m,s in zip(mm,ms)], [m+s for m,s in zip(mm,ms)], color=C_MQTT, alpha=0.15)
        for i in range(len(NODES)):
            ax.annotate(f'{wm[i]:.1f}', (NODES[i], wm[i]), textcoords="offset points", xytext=(0,12),  ha='center', fontsize=9, color=C_WSN)
            ax.annotate(f'{mm[i]:.1f}', (NODES[i], mm[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color=C_MQTT)
        xl  = 'Sensor Dugum Sayisi' if lang=='tr' else 'Number of Sensor Nodes'
        blb = 'golgeli alan = +/-1 std' if lang=='tr' else 'shaded area = +/-1 std'
        ax.set_xlabel(xl, fontsize=11); ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(f'{title} ({blb})', fontsize=12, fontweight='bold')
        ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
        fn = filename.replace('.png', f'_{lang}.png')
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# BROKER IMPACT
# ============================================================
def plot_broker_impact(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        t = 'Araci Etkisi: PDR Karsilastirmasi' if lang=='tr' else 'Broker Impact on PDR'
        fig.suptitle(t, fontsize=14, fontweight='bold')
        for idx, (sc, sc_label) in enumerate([('wsn', 'WSN'), ('mqtt', 'MQTT-SN')]):
            ax = axes[idx]
            no   = [data.get(f"exp1_{sc}_{n}", {}).get('PDR_mean', 0) for n in NODES]
            no_s = [data.get(f"exp1_{sc}_{n}", {}).get('PDR_std',  0) for n in NODES]
            yes  = [data.get(f"exp2_{sc}_{n}", {}).get('PDR_mean', 0) for n in NODES]
            yes_s= [data.get(f"exp2_{sc}_{n}", {}).get('PDR_std',  0) for n in NODES]
            lb_no  = 'Araci Yok' if lang=='tr' else 'No Broker'
            lb_yes = 'Araci Var' if lang=='tr' else 'With Broker'
            c1 = C_WSN  if sc=='wsn' else C_MQTT
            c2 = C_WSN_L if sc=='wsn' else C_MQTT_L
            ax.errorbar(NODES, no,  yerr=no_s,  fmt='o-',  color=c1, lw=2, ms=8, capsize=4, label=f'{sc_label} {lb_no}')
            ax.errorbar(NODES, yes, yerr=yes_s, fmt='o--', color=c2, lw=2, ms=8, capsize=4, label=f'{sc_label} {lb_yes}')
            for i in range(len(NODES)):
                ax.annotate(f'{no[i]:.1f}%',  (NODES[i], no[i]),  textcoords="offset points", xytext=(0,12),  ha='center', fontsize=9)
                ax.annotate(f'{yes[i]:.1f}%', (NODES[i], yes[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9)
            xl = 'Dugum Sayisi' if lang=='tr' else 'Nodes'
            ax.set_xlabel(xl); ax.set_ylabel('PDR (%)')
            tt = f'{sc_label}: {"Araci Etkisi" if lang=="tr" else "Broker Impact"}'
            ax.set_title(tt, fontweight='bold')
            ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
        fn = f'09_broker_impact_{lang}.png'
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# EQUAL LOAD PLOTS
# ============================================================
def plot_equal_load(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        t = 'Esit Yuk Altinda PDR (Araci Yok)' if lang=='tr' else 'Equal Load PDR Comparison (No Broker)'
        fig.suptitle(t, fontsize=14, fontweight='bold')
        for idx, (m, yl) in enumerate([('PDR', 'PDR (%)'), ('Delay', 'Delay (ms)')]):
            ax = axes[idx]
            hm = [data.get(f"exp3_wsn_hetero_{n}", {}).get(f'{m}_mean', 0) for n in NODES]
            hs = [data.get(f"exp3_wsn_hetero_{n}", {}).get(f'{m}_std',  0) for n in NODES]
            mm = [data.get(f"exp1_mqtt_{n}",        {}).get(f'{m}_mean', 0) for n in NODES]
            ms = [data.get(f"exp1_mqtt_{n}",        {}).get(f'{m}_std',  0) for n in NODES]
            lb_h = 'KAA Hetero' if lang=='tr' else 'WSN Hetero'
            ax.errorbar(NODES, hm, yerr=hs, fmt='^-', color=C_HET,  lw=2, ms=8, capsize=4, label=lb_h)
            ax.errorbar(NODES, mm, yerr=ms, fmt='s-', color=C_MQTT, lw=2, ms=8, capsize=4, label='MQTT-SN')
            for i in range(len(NODES)):
                ax.annotate(f'{hm[i]:.1f}', (NODES[i], hm[i]), textcoords="offset points", xytext=(0,12),  ha='center', fontsize=9, color=C_HET)
                ax.annotate(f'{mm[i]:.1f}', (NODES[i], mm[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color=C_MQTT)
            xl = 'Dugum Sayisi' if lang=='tr' else 'Nodes'
            ax.set_xlabel(xl); ax.set_ylabel(yl)
            ax.set_title(yl, fontweight='bold')
            ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
        fn = f'12_equal_load_{lang}.png'
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

def plot_equal_load_broker(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        t = 'Esit Yuk, Araci Var' if lang=='tr' else 'Equal Load with Broker'
        fig.suptitle(t, fontsize=14, fontweight='bold')
        for idx, (m, yl) in enumerate([('PDR', 'PDR (%)'), ('Delay', 'Delay (ms)')]):
            ax = axes[idx]
            hm = [data.get(f"exp3b_wsn_hetero_broker_{n}", {}).get(f'{m}_mean', 0) for n in NODES]
            hs = [data.get(f"exp3b_wsn_hetero_broker_{n}", {}).get(f'{m}_std',  0) for n in NODES]
            mm = [data.get(f"exp2_mqtt_{n}",               {}).get(f'{m}_mean', 0) for n in NODES]
            ms = [data.get(f"exp2_mqtt_{n}",               {}).get(f'{m}_std',  0) for n in NODES]
            lb_h = 'KAA Hetero+Araci' if lang=='tr' else 'WSN Hetero+Broker'
            ax.errorbar(NODES, hm, yerr=hs, fmt='^-', color=C_HET,  lw=2, ms=8, capsize=4, label=lb_h)
            ax.errorbar(NODES, mm, yerr=ms, fmt='s-', color=C_MQTT, lw=2, ms=8, capsize=4, label='MQTT-SN+Broker')
            for i in range(len(NODES)):
                ax.annotate(f'{hm[i]:.1f}', (NODES[i], hm[i]), textcoords="offset points", xytext=(0,12),  ha='center', fontsize=9, color=C_HET)
                ax.annotate(f'{mm[i]:.1f}', (NODES[i], mm[i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color=C_MQTT)
            xl = 'Dugum Sayisi' if lang=='tr' else 'Nodes'
            ax.set_xlabel(xl); ax.set_ylabel(yl)
            ax.set_title(yl, fontweight='bold')
            ax.set_xticks(NODES); ax.legend(); ax.grid(alpha=0.3)
        fn = f'13_equal_load_broker_{lang}.png'
        plt.tight_layout(); plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight'); plt.close()
        print(f"[OK] {fn}")

# ============================================================
# HIERARCHY SWEEP PLOT (Direction 1)
# ============================================================
def plot_hier_sweep(hier_data):
    """Bar chart + line: PDR and Delay vs numLocalBrokers at 200 nodes."""
    node = 200
    lbs  = [lb for lb in LB_VALUES if f"hier_lb{lb}_{node}" in hier_data]
    if not lbs:
        print("[SKIP] No hierarchy data found.")
        return

    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        t = f'Cok Katmanli Broker Hiyerarsisi — {node} Dugum' if lang=='tr' \
            else f'Multi-Broker Hierarchy Sweep — {node} Nodes'
        fig.suptitle(t, fontsize=14, fontweight='bold')

        pdrs  = [hier_data[f"hier_lb{lb}_{node}"]['PDR_mean']   for lb in lbs]
        pstds = [hier_data[f"hier_lb{lb}_{node}"]['PDR_std']    for lb in lbs]
        dels  = [hier_data[f"hier_lb{lb}_{node}"]['Delay_mean'] for lb in lbs]
        dstds = [hier_data[f"hier_lb{lb}_{node}"]['Delay_std']  for lb in lbs]
        nruns = hier_data[f"hier_lb{lbs[0]}_{node}"]['n_runs']

        colors = [C_HIER.get(lb, '#555555') for lb in lbs]
        x = np.arange(len(lbs))
        w = 0.5

        # PDR bar
        ax = axes[0]
        bars = ax.bar(x, pdrs, w, yerr=pstds, capsize=5,
                      color=colors, edgecolor='white', alpha=0.85, zorder=3)
        for i, (v, s) in enumerate(zip(pdrs, pstds)):
            ax.text(x[i], v+s+0.4, f'{v:.1f}%', ha='center', fontsize=9, fontweight='bold')
        ax.set_xticks(x)
        xl_lb = 'Yerel Broker Sayisi' if lang=='tr' else 'Number of Local Brokers'
        ax.set_xticklabels([str(lb) for lb in lbs])
        ax.set_xlabel(xl_lb, fontsize=11)
        ax.set_ylabel('PDR (%)', fontsize=11)
        ax.set_title('PDR vs Local Brokers', fontweight='bold')
        ax.set_ylim(0, 105)
        ax.grid(axis='y', alpha=0.3, zorder=0)
        nr_lbl = f'({nruns} {"tohum" if lang=="tr" else "seeds"}, mean+/-std)'
        ax.text(0.98, 0.02, nr_lbl, transform=ax.transAxes,
                ha='right', va='bottom', fontsize=8, color='gray')

        # Delay bar
        ax2 = axes[1]
        ax2.bar(x, dels, w, yerr=dstds, capsize=5,
                color=colors, edgecolor='white', alpha=0.85, zorder=3)
        for i, (v, s) in enumerate(zip(dels, dstds)):
            ax2.text(x[i], v+s+1, f'{v:.1f}', ha='center', fontsize=9, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([str(lb) for lb in lbs])
        ax2.set_xlabel(xl_lb, fontsize=11)
        yl_d = 'Gecikme (ms)' if lang=='tr' else 'Avg Delay (ms)'
        ax2.set_ylabel(yl_d, fontsize=11)
        ax2.set_title('Delay vs Local Brokers', fontweight='bold')
        ax2.grid(axis='y', alpha=0.3, zorder=0)

        fn = f'15_hier_sweep_{lang}.png'
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR_HIER, fn), dpi=DPI, bbox_inches='tight')
        plt.close()
        print(f"[OK] {fn}")

def plot_hier_vs_wsn(data, hier_data):
    """Compare: WSN single-broker vs MQTT-SN single-broker vs MQTT-SN best hierarchy at 200 nodes."""
    node = 200
    lbs  = [lb for lb in LB_VALUES if f"hier_lb{lb}_{node}" in hier_data]
    if not lbs: return

    for lang in ['tr', 'en']:
        fig, ax = plt.subplots(figsize=(10, 5))
        t = f'Mimari Karsilastirma — {node} Dugum' if lang=='tr' \
            else f'Architecture Comparison at {node} Nodes'
        ax.set_title(t, fontsize=13, fontweight='bold')

        # WSN single broker (baseline from Set 2)
        wsn_pdr  = data.get(f"exp2_wsn_{node}",  {}).get('PDR_mean', 0)
        wsn_std  = data.get(f"exp2_wsn_{node}",  {}).get('PDR_std',  0)
        mqtt_pdr = data.get(f"exp2_mqtt_{node}", {}).get('PDR_mean', 0)
        mqtt_std = data.get(f"exp2_mqtt_{node}", {}).get('PDR_std',  0)

        labels = (['WSN\n(tek aracı)' if lang=='tr' else 'WSN\n(single broker)'] +
                  ['MQTT-SN\n(tek aracı)' if lang=='tr' else 'MQTT-SN\n(single broker)'] +
                  [f'MQTT-SN\nLB={lb}' for lb in lbs])
        means  = [wsn_pdr, mqtt_pdr] + [hier_data[f"hier_lb{lb}_{node}"]['PDR_mean'] for lb in lbs]
        stds   = [wsn_std, mqtt_std] + [hier_data[f"hier_lb{lb}_{node}"]['PDR_std']  for lb in lbs]
        colors = [C_WSN, C_MQTT] + [C_HIER.get(lb, '#555555') for lb in lbs]

        x = np.arange(len(labels))
        bars = ax.bar(x, means, 0.55, yerr=stds, capsize=5,
                      color=colors, edgecolor='white', alpha=0.87, zorder=3)
        for i, (v, s) in enumerate(zip(means, stds)):
            ax.text(x[i], v+s+0.5, f'{v:.1f}%', ha='center', fontsize=9, fontweight='bold',
                    color=colors[i])
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
        yl = 'PDR (%)' ; ax.set_ylabel(yl, fontsize=11)
        ax.set_ylim(0, 105)
        ax.grid(axis='y', alpha=0.3, zorder=0)

        # Horizontal reference lines
        ax.axhline(wsn_pdr,  color=C_WSN,  linestyle='--', alpha=0.4, lw=1.2)
        ax.axhline(mqtt_pdr, color=C_MQTT, linestyle='--', alpha=0.4, lw=1.2)

        fn = f'16_hier_vs_wsn_{lang}.png'
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR_HIER, fn), dpi=DPI, bbox_inches='tight')
        plt.close()
        print(f"[OK] {fn}")

# ============================================================
# DASHBOARD
# ============================================================
def plot_dashboard(data):
    for lang in ['tr', 'en']:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        t = 'KAA ile MQTT-SN Istatistiksel Karsilastirma Panosu' if lang=='tr' \
            else 'WSN vs MQTT-SN Statistical Comparison Dashboard'
        fig.suptitle(t, fontsize=16, fontweight='bold')
        if lang == 'tr':
            scen = [
                ('exp1_wsn',          'KAA Sabit A.Yok',   C_WSN,   'o-'),
                ('exp1_mqtt',         'MQTT-SN A.Yok',     C_MQTT,  's-'),
                ('exp3_wsn_hetero',   'KAA Hetero A.Yok',  C_HET,   '^-'),
                ('exp2_wsn',          'KAA Sabit A.Var',   C_WSN_L, 'o--'),
                ('exp2_mqtt',         'MQTT-SN A.Var',     C_MQTT_L,'s--'),
            ]
            panels = [
                (axes[0,0], 'PDR',        'PDR (%)',         'Paket Teslim Orani'),
                (axes[0,1], 'Delay',      'Gecikme (ms)',    'Uctan Uca Gecikme'),
                (axes[1,0], 'Throughput', 'Verim (kbps)',    'Ag Verimi'),
                (axes[1,1], 'Dead',       'Basarisiz Akis',  'Basarisiz Akis Sayisi'),
            ]
        else:
            scen = [
                ('exp1_wsn',          'WSN Const. No Broker',   C_WSN,   'o-'),
                ('exp1_mqtt',         'MQTT-SN No Broker',      C_MQTT,  's-'),
                ('exp3_wsn_hetero',   'WSN Hetero No Broker',   C_HET,   '^-'),
                ('exp2_wsn',          'WSN Const. W/Broker',    C_WSN_L, 'o--'),
                ('exp2_mqtt',         'MQTT-SN W/Broker',       C_MQTT_L,'s--'),
            ]
            panels = [
                (axes[0,0], 'PDR',        'PDR (%)',        'Packet Delivery Ratio'),
                (axes[0,1], 'Delay',      'Delay (ms)',     'End-to-End Delay'),
                (axes[1,0], 'Throughput', 'Throughput (kbps)', 'Network Throughput'),
                (axes[1,1], 'Dead',       'Dead Flows',     'Dead Flow Count'),
            ]
        for ax, m, yl, tt in panels:
            for pf, lb, cl, st in scen:
                mn = [data.get(f"{pf}_{n}", {}).get(f'{m}_mean', 0) for n in NODES]
                ax.plot(NODES, mn, st, color=cl, linewidth=1.8, markersize=7, label=lb)
            ax.set_xlabel('Nodes', fontsize=10); ax.set_ylabel(yl, fontsize=10)
            ax.set_title(tt, fontweight='bold', fontsize=11)
            ax.set_xticks(NODES); ax.legend(fontsize=8); ax.grid(alpha=0.3)
        fn = f'10_dashboard_{lang}.png'
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, fn), dpi=DPI, bbox_inches='tight')
        plt.close()
        print(f"[OK] {fn}")

# ============================================================
# PRINT RESULTS
# ============================================================
def print_results(data, hier_data):
    for lang in ['tr', 'en']:
        sep = "="*120
        print(f"\n{sep}")
        if lang == 'tr':
            print("  KAA ile MQTT-SN ISTATISTIKSEL KARSILASTIRMA (TURKCE)")
        else:
            print("  WSN vs MQTT-SN STATISTICAL COMPARISON (ENGLISH)")
        print(sep)

        # Sets 1 & 2
        for s in [1, 2]:
            sn = ("ARACI YOK" if s==1 else "ARACI VAR") if lang=='tr' \
                 else ("NO BROKER" if s==1 else "WITH BROKER")
            kume = "KUME" if lang=='tr' else "SET"
            print(f"\n  --- {kume} {s}: {sn} ---")
            if lang == 'tr':
                print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA PDR':<20} {'MQTT PDR':<20} {'p(PDR)':<8} {'KAA Gec.':<20} {'MQTT Gec.':<20} {'p(Gec)':<8}")
            else:
                print(f"  {'Nodes':<8} {'Seeds':<6} {'WSN PDR':<20} {'MQTT PDR':<20} {'p(PDR)':<8} {'WSN Delay':<20} {'MQTT Delay':<20} {'p(Del)':<8}")
            print("  "+"-"*110)
            for n in NODES:
                w  = data.get(f"exp{s}_wsn_{n}",  {})
                m  = data.get(f"exp{s}_mqtt_{n}", {})
                nr = w.get('n_runs', 0)
                wp = f"{w.get('PDR_mean',0):.1f}+/-{w.get('PDR_std',0):.1f}%"
                mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
                wd = f"{w.get('Delay_mean',0):.1f}+/-{w.get('Delay_std',0):.1f}ms"
                md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
                p_pdr = welch_ttest(data, f"exp{s}_wsn_{n}", f"exp{s}_mqtt_{n}", 'PDR')
                p_del = welch_ttest(data, f"exp{s}_wsn_{n}", f"exp{s}_mqtt_{n}", 'Delay')
                pp = f"{p_pdr:.4f}" if p_pdr is not None else "N/A"
                pd_v = f"{p_del:.4f}" if p_del is not None else "N/A"
                print(f"  {n:<8} {nr:<6} {wp:<20} {mp:<20} {pp:<8} {wd:<20} {md:<20} {pd_v:<8}")

        # Set 3
        hdr3 = "KUME 3: ESIT YUK, ARACI YOK" if lang=='tr' \
               else "SET 3: EQUAL LOAD, NO BROKER (WSN Hetero vs MQTT-SN)"
        print(f"\n  --- {hdr3} ---")
        if lang=='tr':
            print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA Het. PDR':<22} {'MQTT-SN PDR':<22} {'p(PDR)':<8} {'KAA Het. Gec.':<22} {'MQTT-SN Gec.':<22}")
        else:
            print(f"  {'Nodes':<8} {'Seeds':<6} {'WSN Het. PDR':<22} {'MQTT-SN PDR':<22} {'p(PDR)':<8} {'WSN Het. Delay':<22} {'MQTT-SN Delay':<22}")
        print("  "+"-"*110)
        for n in NODES:
            h  = data.get(f"exp3_wsn_hetero_{n}", {})
            m  = data.get(f"exp1_mqtt_{n}",        {})
            nr = h.get('n_runs', 0)
            hp = f"{h.get('PDR_mean',0):.1f}+/-{h.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            hd = f"{h.get('Delay_mean',0):.1f}+/-{h.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            p_pdr = welch_ttest(data, f"exp3_wsn_hetero_{n}", f"exp1_mqtt_{n}", 'PDR')
            pp = f"{p_pdr:.4f}" if p_pdr is not None else "N/A"
            print(f"  {n:<8} {nr:<6} {hp:<22} {mp:<22} {pp:<8} {hd:<22} {md:<22}")

        # Set 3b
        hdr3b = "KUME 3b: ESIT YUK, ARACI VAR" if lang=='tr' \
                else "SET 3b: EQUAL LOAD, WITH BROKER (WSN Het.+Broker vs MQTT-SN+Broker)"
        print(f"\n  --- {hdr3b} ---")
        if lang=='tr':
            print(f"  {'Dugum':<8} {'Tohum':<6} {'KAA Het.+A PDR':<22} {'MQTT+A PDR':<22} {'p(PDR)':<8} {'KAA Het.+A Gec.':<22} {'MQTT+A Gec.':<22}")
        else:
            print(f"  {'Nodes':<8} {'Seeds':<6} {'WSN Het.+B PDR':<22} {'MQTT+B PDR':<22} {'p(PDR)':<8} {'WSN Het.+B Del.':<22} {'MQTT+B Del.':<22}")
        print("  "+"-"*110)
        for n in NODES:
            h  = data.get(f"exp3b_wsn_hetero_broker_{n}", {})
            m  = data.get(f"exp2_mqtt_{n}", {})
            nr = h.get('n_runs', 0)
            hp = f"{h.get('PDR_mean',0):.1f}+/-{h.get('PDR_std',0):.1f}%"
            mp = f"{m.get('PDR_mean',0):.1f}+/-{m.get('PDR_std',0):.1f}%"
            hd = f"{h.get('Delay_mean',0):.1f}+/-{h.get('Delay_std',0):.1f}ms"
            md = f"{m.get('Delay_mean',0):.1f}+/-{m.get('Delay_std',0):.1f}ms"
            p_pdr = welch_ttest(data, f"exp3b_wsn_hetero_broker_{n}", f"exp2_mqtt_{n}", 'PDR')
            pp = f"{p_pdr:.4f}" if p_pdr is not None else "N/A"
            print(f"  {n:<8} {nr:<6} {hp:<22} {mp:<22} {pp:<8} {hd:<22} {md:<22}")

        # ── SET 5: Multi-Broker Hierarchy ──
        if hier_data:
            node = 200
            hdr5 = "KUME 5: COK KATMANLI BROKER HIYERARSISI (200 Dugum)" if lang=='tr' \
                   else "SET 5: MULTI-BROKER HIERARCHY (200 Nodes, MQTT-SN)"
            print(f"\n  --- {hdr5} ---")
            note = "  (* p degerleri tek aracili baseline ile karsilastirilmistir)" if lang=='tr' \
                   else "  (* p-values compared against single-broker baseline LB=1)"
            print(note)
            if lang=='tr':
                print(f"  {'LB':<6} {'Tohum':<6} {'MQTT-SN PDR':<22} {'p(LB vs LB=1)':<18} {'MQTT-SN Gec.':<22} {'p(Del vs LB=1)':<18}")
            else:
                print(f"  {'LB':<6} {'Seeds':<6} {'MQTT-SN PDR':<22} {'p(LB vs LB=1)':<18} {'MQTT-SN Delay':<22} {'p(Del vs LB=1)':<18}")
            print("  "+"-"*100)
            for lb in LB_VALUES:
                key = f"hier_lb{lb}_{node}"
                if key not in hier_data: continue
                h  = hier_data[key]
                nr = h['n_runs']
                hp = f"{h['PDR_mean']:.1f}+/-{h['PDR_std']:.1f}%"
                hd = f"{h['Delay_mean']:.1f}+/-{h['Delay_std']:.1f}ms"
                # Compare against LB=1 baseline
                if lb == 1:
                    pp = "baseline"
                    pd_v = "baseline"
                else:
                    p_pdr = welch_ttest(hier_data, f"hier_lb1_{node}", key, 'PDR')
                    p_del = welch_ttest(hier_data, f"hier_lb1_{node}", key, 'Delay')
                    pp   = f"{p_pdr:.4f} ({sig_label(p_pdr)})" if p_pdr is not None else "N/A"
                    pd_v = f"{p_del:.4f} ({sig_label(p_del)})" if p_del is not None else "N/A"
                print(f"  {lb:<6} {nr:<6} {hp:<22} {pp:<18} {hd:<22} {pd_v:<18}")

        print(f"\n{sep}\n")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("\n[MIoT] WSN vs MQTT-SN + Multi-Broker Hierarchy Analysis\n")
    os.makedirs(OUTPUT_DIR,      exist_ok=True)
    os.makedirs(OUTPUT_DIR_HIER, exist_ok=True)

    data      = load_all()
    hier_data = load_hier_set(LB_VALUES, node=200)

    if len(data) == 0:
        print("[ERROR] No main experiment data found!")
        sys.exit(1)

    # ── Original plots ──
    plot_bars(data, 1, 'PDR',   'PDR (%)',       'PDR (%)',
              'Paket Teslim Orani: KAA ve MQTT-SN - Araci Yok',
              'PDR: WSN vs MQTT-SN - No Broker',   '01_set1_pdr_bar.png')
    plot_bars(data, 1, 'Delay', 'Gecikme (ms)',  'Delay (ms)',
              'Gecikme: KAA ve MQTT-SN - Araci Yok',
              'Delay: WSN vs MQTT-SN - No Broker', '02_set1_delay_bar.png')
    plot_lines(data, 1, 'PDR',  'PDR (%)',       'PDR (%)',
               'PDR Olceklenebilirligi - Araci Yok',
               'PDR Scalability - No Broker',       '04_set1_pdr_line.png')
    plot_lines(data, 1, 'Delay','Gecikme (ms)',  'Delay (ms)',
               'Gecikme Olceklenebilirligi - Araci Yok',
               'Delay Scalability - No Broker',     '04b_set1_delay_line.png')
    plot_bars(data, 2, 'PDR',   'PDR (%)',       'PDR (%)',
              'Paket Teslim Orani: KAA ve MQTT-SN - Araci Var',
              'PDR: WSN vs MQTT-SN - With Broker',  '05_set2_pdr_bar.png')
    plot_bars(data, 2, 'Delay', 'Gecikme (ms)',  'Delay (ms)',
              'Gecikme: KAA ve MQTT-SN - Araci Var',
              'Delay: WSN vs MQTT-SN - With Broker','06_set2_delay_bar.png')
    plot_lines(data, 2, 'PDR',  'PDR (%)',       'PDR (%)',
               'PDR Olceklenebilirligi - Araci Var',
               'PDR Scalability - With Broker',      '08_set2_pdr_line.png')
    plot_lines(data, 2, 'Delay','Gecikme (ms)',  'Delay (ms)',
               'Gecikme Olceklenebilirligi - Araci Var',
               'Delay Scalability - With Broker',   '08b_set2_delay_line.png')
    plot_broker_impact(data)
    plot_dashboard(data)
    plot_equal_load(data)
    plot_equal_load_broker(data)

    # ── Hierarchy plots (only if data exists) ──
    if hier_data:
        plot_hier_sweep(hier_data)
        plot_hier_vs_wsn(data, hier_data)
    else:
        print("[INFO] No hierarchy data — skipping hierarchy plots.")
        print("[INFO] Run Set 5 experiments first: scripts/run-comparison.sh")

    print_results(data, hier_data)
