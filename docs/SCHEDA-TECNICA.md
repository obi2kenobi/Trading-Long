---
repo: Trading-Long
linguaggi: Python 3, Pine Script (v6)
stato: in uso (backtest parziale, senza rete)
aggiornato: 2026-11-26
---

## Scopo
Strategie Pine Script (long) e backtest Python in `backtest/`. Obiettivo: strategie di breakout/trend-follow su SPY/QQQ/IWM con backtest walk-forward.

## Architettura
- Radice: 5 file `.pine` (strategie long), `CLAUDE.md`
- `backtest/src/`: 13 moduli Python (engine, strategy, metrics, optimize, walk_forward, global_optimize, pine_ta, check_data, download_data, run_baseline, run_atr_baseline, compare_baseline_vs_optimized)
- `backtest/reports/`: 31 CSV di report (baseline, sweep, walk-forward)
- `backtest/data/`: dati OHLCV gitignored (rigenerabili)
- `tools/py-gate.sh`: gate sintassi Python
- `docs/`: guida LLM, inventario, archivio

## Componenti
| nome | ruolo | file |
|---|---|---|
| GOLDEN-CROSS LONG | trend-follow SMA cross | GOLDEN-CROSS LONG.pine |
| TEMA-ST-WT LONG OPT | optimized anti-late-entry | TEMA-ST-WT LONG OPT.pine |
| TIGHT-BREAKOUT LONG | breakout bull-regime Fineco | TIGHT-BREAKOUT LONG.pine |
| TIGHT-BREAKOUT LONG v8.1 | v8.1 Fineco + ratchet trail | TIGHT-BREAKOUT LONG v8.1.pine |
| TIGHT-BREAKOUT MINIMAL v8.2 | minimale 1 entry/1 exit | TIGHT-BREAKOUT MINIMAL v8.2.pine |
| backtest_engine | moteur bar-by-bar (signal-at-close → fill-at-next-open) | backtest/src/backtest_engine.py |
| strategy | parametri ATR-multipli all'entry | backtest/src/strategy.py |
| metrics | metriche di performance | backtest/src/metrics.py |
| optimize / global_optimize | ottimizzazione parametri | backtest/src/optimize.py, global_optimize.py |
| walk_forward | walk-forward validation | backtest/src/walk_forward.py |
| pine_ta | helper tasto Pine | backtest/src/pine_ta.py |
| check_data / download_data | validazione/download dati | backtest/src/check_data.py, download_data.py |
| run_baseline / run_atr_baseline | run baseline | backtest/src/run_baseline.py, run_atr_baseline.py |
| compare_baseline_vs_optimized | confronto baseline vs ottimizzato | backtest/src/compare_baseline_vs_optimized.py |

## Dati e interfacce
- Dati OHLCV Yahoo Finance (yfinance), gitignored in `backtest/data/`
- Interfacce: CLI comandi `python3 backtest/src/<entrypoint>.py`; Pine Script v6 consumato su TradingView
- CSV in `backtest/reports/` (baseline, sweep, walk-forward)

## Dipendenze
- Python 3 (non pinnate in requirements.txt; non verificato)
- yfinance, pandas, numpy (non pinnate; non verificato, installare manualmente)
- Pine Script v6 (target TradingView)

## Configurazione
- Nessuna variabile d'ambiente richiesta (nessun `.env`)
- Segreti: nessuno nel repo

## Build e test
- `bash tools/py-gate.sh .` → OK (13 file compilano), exit 0 — verificato 2026-11-26
- `wc -l *.pine` → v8.2 MINIMAL = 122 righe (verificato)
- Non verificato (rete/dati): install pip, download_data.py, check_data.py, run_baseline.py, global_optimize.py, walk_forward.py, compare_baseline_vs_optimized.py

## Deploy
Non applicabile: repo di strategie e backtest, nessun deploy. Le strategie Pine sono copiate su TradingView manualmente.

## Rischi e debito tecnico
- Dipendenza da yfinance (rete): senza rete nessun backtest eseguibile
- Dipendenze non pinnate / nessun requirements.txt
- `docs/archivio/SAL.md` (superato) cita numeri non riconducibili al codice — non citare
- v8.2 MINIMAL: 122 righe (SAL.md diceva 50) — verificare prima di citare
- Dati OHLCV rigenerabili ma non versionati
