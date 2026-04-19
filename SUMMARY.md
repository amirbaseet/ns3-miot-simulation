# SAUCIS Hardening Bundle — Summary

Drop-in replacements and one new file for `ns3-miot-simulation`, produced
from an audit of the actual uploaded repository state (not the older
GitHub web snapshot). All edits are behaviour-compatible; no source-code
logic or experimental data was touched.

---

## Two ways to apply

### Option A — copy files over (simplest)

```bash
cd ~/ns3-miot-simulation
unzip -o /path/to/saucis_hardening_bundle.zip -d /tmp/
rsync -av /tmp/saucis_hardening_bundle/ ./ \
    --exclude saucis_hardening.patch --exclude SUMMARY.md
chmod +x scripts/run-comparison.sh
git status           # review
```

### Option B — apply the unified patch

```bash
cd ~/ns3-miot-simulation
patch -p2 --dry-run < /path/to/saucis_hardening.patch    # verify clean
patch -p2            < /path/to/saucis_hardening.patch
chmod +x scripts/run-comparison.sh
git status
```

Dry-run note: the patch was generated from the uploaded zip. If your
local `main` has diverged from that snapshot, re-run the audit diff
against the new `main` first.

---

## What each file does

| File | Change |
|------|--------|
| `.gitignore` | Expanded from 82 B to cover ns-3 build artifacts (`*.a`, `*.so`, `CMakeCache.txt`, etc.), Python venv, `.ipynb_checkpoints/`, `.vscode/`, `.idea/`, OS junk (`.DS_Store`, `Thumbs.db`). Keeps the existing `/*.zip` exclusion. |
| `CITATION.cff` | Added Amro ORCID, affiliation strings, keywords, and a placeholder `doi: 10.5281/zenodo.PENDING` to be filled after Zenodo mints the v1.0 DOI. `preferred-citation` now includes ORCIDs. |
| `README.md` | (1) Badge row under the H2 (License, ns-3 v3.40, Python 3.10+, 270-run count, DOI placeholder). (2) "See REPRODUCE.md" pointer at the top of Quick Start. (3) Python requirement line now points at `requirements.txt`. (4) Key Finding #2 softened to match the paper's "ties at 200 nodes (p=0.2601 ns)" phrasing. (5) Duplicate/broken CSV schema section replaced with **one** clean section including the verified `mean ≈ 67.35 %` reproduction example. (6) Zenodo `@software` BibTeX entry added alongside the paper BibTeX. |
| `REPRODUCE.md` | New file — end-to-end recipe from fresh Ubuntu → compiled ns-3 v3.40 → all 270 runs → all figures, with wall-time estimates, a smoke test, CSV-count verification, paper-cell spot-check, and troubleshooting section. |
| `scripts/analyze_comparison.py` | Expanded module docstring: paper reference, exact input file patterns (all 270 CSVs), expected outputs, usage example with `tee`, note that Set 5 LB=1 baseline reuses Set 2 data (disclosed in paper §5.7). |
| `scripts/run-comparison.sh` | (1) Proper banner with paper ref, prerequisites, wall-time estimates. (2) `set -uo pipefail` (NOT `-e` — a single simulation hiccup must not abort an 8-hour batch). (3) Real `--set5-only` flag and `--help`. (4) Set 5 loop changed from `LB in 1 2 4 5` to `LB in 2 4 5` — LB=1 baseline is reused from Set 2 MQTT-SN data (consistent with paper and committed CSVs). |

---

## Still to do manually (outside the bundle)

| # | Action | Where |
|:-:|--------|-------|
| 1 | Set About panel — description, topics, website | GitHub web UI (repo "About" cog) |
| 2 | Tag `v1.0-saucis-submission` and push | `git tag -a …` + `git push origin <tag>` |
| 3 | Toggle Zenodo ↔ GitHub integration ON for this repo | https://zenodo.org/account/settings/github/ |
| 4 | Draft a Release from the tag | GitHub → Releases → Draft |
| 5 | Replace `10.5281/zenodo.PENDING` (in `CITATION.cff`) and `pending%20Zenodo` (in `README.md` DOI badge) with the real DOI Zenodo mints | Two one-line edits, commit, push |

After (5) the ready-to-submit checklist is 10/10 green.

---

## Verification performed

| Check | Result |
|-------|--------|
| `bash -n scripts/run-comparison.sh` | OK |
| `python3 -c "import ast; ast.parse(open('scripts/analyze_comparison.py').read())"` | OK |
| `python3 -c "import yaml; yaml.safe_load(open('CITATION.cff'))"` | OK |
| `patch --dry-run -p2 < saucis_hardening.patch` | All 6 files apply cleanly |
| Aggregate PDR for Set 2, 200-node WSN across 10 committed CSVs | 67.35 ± 7.88 % (paper: 67.4 ± 8.3 %) ✓ |
| File counts on disk | 80 + 80 + 40 + 40 + 30 = 270 ✓ |
| No `exp_hier_lb1_*.csv` in `experiments/hier/` | Confirmed — consistent with updated Set 5 loop |
