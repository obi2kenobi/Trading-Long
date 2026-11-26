# LLM-GUIDA — Trading-Long

## Scopo
Repo di strategie Pine Script (long) + backtest Python in `backtest/`. Obiettivo: strategie di breakout/trend-follow su SPY/QQQ/IWM con backtest walk-forward.

## Struttura (dal grafo ~/graphify-out/Trading-Long/graph.json)
- Radice: `CLAUDE.md` (regole di lavoro), 5 file `.pine` (TEMA-ST-WT LONG OPT, GOLDEN-CROSS, TIGHT-BREAKOUT v8.1/v8.2 MINIMAL, TIGHT-BREAKOUT LONG)
- `backtest/src/`: 13 file Python (engine, strategy, metrics, optimize, walk_forward, global_optimize, pine_ta, check_data, download_data, run_baseline, run_atr_baseline, compare_baseline_vs_optimized)
- `backtest/reports/`: 31 CSV di report (baseline, sweep, walk-forward)
- `tools/py-gate.sh`: gate sintassi .py
- `docs/archivio/`: documenti superati (SAL.md)

## Come si avvia / si testa (SOLO comandi verificati in questa revisione)
- `bash tools/py-gate.sh .` → "Sintassi python: tutti i .py compilano (13 file)", exit 0
- `wc -l *.pine` → v8.2 MINIMAL = 122 righe
- `git log --oneline -1` → 602a156 (docs: add README)
- NON verificato (non eseguiti, richiedono rete/dati): `pip install yfinance pandas numpy`; `python3 src/download_data.py`; `python3 src/check_data.py`; `python3 src/run_baseline.py`; `python3 src/global_optimize.py`; `python3 src/compare_baseline_vs_optimized.py`

## Convenzioni
- Commit `<type>: <descrizione>` (feat/fix/refactor/docs/test/chore)
- Pine: header con @version, @description, @author; 1 file per strategia; toggle ON di default
- Backtest: parametri ATR-multipli catturati all'entry; engine bar-by-bar (signal-at-close → fill-at-next-open)
- Dati Yahoo Finance gitignored in `backtest/data/` (rigenerabili)

## Punti fragili
- Dipendenza da yfinance (rete) per i dati; senza rete nessun backtest eseguibile
- SAL.md (superato) conteneva numeri di backtest non riconducibili al codice
- v8.2 MINIMAL: 122 righe (SAL.md diceva 50) — verificare prima di citare numeri

## Documenti superati
- `SAL.md` (2026-05-01): spostato in `docs/archivio/SAL.md` — log datato con affermazioni smentite (50 righe vs 122; DD -15% vs 25%; branch claude/review-script-work-OqTza assente; header v6.5 vs v6.6)

> Istruzioni d'uso dettagliate: `docs/ISTRUZIONI.md`.

Scheda tecnica sintetica: `docs/SCHEDA-TECNICA.md`.
