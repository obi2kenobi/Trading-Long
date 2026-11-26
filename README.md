# Trading-Long

Strategie Pine Script (long) e backtest Python in `backtest/`. Obiettivo: strategie di breakout/trend-follow su SPY/QQQ/IWM con backtest walk-forward.

## Requisiti

- Python 3 (per il backtest)
- Dipendenze di `backtest/`: `yfinance`, `pandas`, `numpy` (non pinnate in un requirements.txt nel repo — non verificato, installare manualmente)
- Nessun file `.env` richiesto per l'uso base

## Installazione

```bash
cd backtest
pip install yfinance pandas numpy
```

## Uso

Gate sintassi dei file Python:

```bash
bash tools/py-gate.sh .
```

Download dati OHLCV (Yahoo Finance, rete richiesta):

```bash
python3 backtest/src/download_data.py
```

Verifica dati:

```bash
python3 backtest/src/check_data.py
```

Backtest baseline / ottimizzazione / walk-forward (comandi indicativi, non tutti verificati senza rete). Si lanciano dalla radice del repo: ogni script aggiunge `backtest/` al `sys.path` (es. `backtest/src/run_baseline.py:7`), quindi gli import `src.*` funzionano da qualsiasi cartella:

```bash
python3 backtest/src/run_baseline.py
python3 backtest/src/global_optimize.py
python3 backtest/src/walk_forward.py
```

Per il dettaglio degli entry point, convenzioni e punti delicati vedere `docs/LLM-GUIDA.md`. Istruzioni d'uso: `docs/ISTRUZIONI.md`.

## Struttura delle cartelle

- `*.pine` — 5 file Pine Script (strategie long) a radice
- `backtest/src/` — 13 moduli Python (engine, strategy, metrics, optimize, walk_forward, global_optimize, pine_ta, check_data, download_data, run_baseline, run_atr_baseline, compare_baseline_vs_optimized)
- `backtest/reports/` — CSV di report (baseline, sweep, walk-forward)
- `.gitignore`: solo `backtest/.gitignore` (ignora `data/`, `__pycache__/`, `*.pyc`, `reports/*.html`, `reports/*.png`); nessun `.gitignore` alla radice
- `backtest/data/` — dati OHLCV (gitignored, rigenerabili)
- `tools/py-gate.sh` — gate sintassi Python
- `docs/` — guida LLM e archivio
- `CLAUDE.md` — regole di lavoro

Scheda tecnica sintetica: `docs/SCHEDA-TECNICA.md`.
