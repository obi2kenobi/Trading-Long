# CLAUDE.md — Trading-Long

## Scopo
Strategie Pine Script (long) + backtest Python in `backtest/`. Obiettivo: breakout/trend-follow su SPY/QQQ/IWM con backtest walk-forward.

## Struttura
- Radice: 5 file `.pine` (strategie long), `CLAUDE.md`
- `backtest/src/`: 13 moduli Python (engine, strategy, metrics, optimize, walk_forward, global_optimize, pine_ta, check_data, download_data, run_baseline, run_atr_baseline, compare_baseline_vs_optimized)
- `backtest/reports/`: 31 CSV di report
- `.gitignore`: solo `backtest/.gitignore` (ignora `data/`, `__pycache__/`, `*.pyc`, `reports/*.html`, `reports/*.png`); nessun `.gitignore` alla radice
- `backtest/data/`: dati OHLCV gitignored (rigenerabili)
- `tools/py-gate.sh`: gate sintassi Python
- `docs/`: LLM-GUIDA.md, _inventario.tsv, _guida-lista.txt, _revisione.tsv, REGOLE-CLAUDE-originale.md, archivio/

## Comandi (verificati)
- `bash tools/py-gate.sh .` → "Sintassi python: tutti i .py compilano (13 file)", exit 0
- `wc -l *.pine` → v8.2 MINIMAL = 122 righe
- Non verificato (rete): `pip install yfinance pandas numpy`; `download_data.py`; `check_data.py`; `run_baseline.py`; `global_optimize.py`; `walk_forward.py`; `compare_baseline_vs_optimized.py`

## Convenzioni
- Commit `<type>: <descrizione>` (feat/fix/refactor/docs/test/chore)
- Pine: header @version/@description/@author; 1 file per strategia; toggle ON default
- Backtest: parametri ATR-multipli all'entry; bar-by-bar (signal-at-close → fill-at-next-open)

## Cosa non toccare
- `backtest/data/` (gitignored)
- `docs/archivio/` (documenti superati; non modificare)
- Niente push e niente cancellazioni

## Segreti
Nessun file `.env` richiesto; nessun segreto nel repo. Se servissero chiavi (es. Yahoo), usare segnaposto in `.env.example`, mai valori reali nel repo.

## Dettaglio
Vedi `docs/LLM-GUIDA.md` per guida operativa, punti fragili e documenti superati.
