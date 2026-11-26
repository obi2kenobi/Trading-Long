---
repo: Trading-Long
software:
  - pine-strategia (5 file .pine)
  - backtest (pacchetto Python in backtest/src/)
  - py-gate.sh
aggiornato: 2026-11-25
---

# Istruzioni d'uso — Trading-Long

Strategie Pine Script (long) + backtest Python in `backtest/`. Obiettivo: breakout/trend-follow su SPY/QQQ/IWM con backtest walk-forward.

## pine-strategia

### Requisiti
TradingView (per l'editor Pine). Nessun segreto.

### Installazione
Nessuna installazione: copiare i file `.pine` in TradingView.

### Avvio
Aprire il file in TradingView, incollare nell'editor e salvare come strategia. File disponibili a radice:
- GOLDEN-CROSS LONG.pine
- TEMA-ST-WT LONG OPT.pine
- TIGHT-BREAKOUT LONG.pine
- TIGHT-BREAKOUT LONG v8.1.pine
- TIGHT-BREAKOUT MINIMAL v8.2.pine

### Uso
Ogni strategia è un file singolo con header `@version`/`@description`/`@author` e toggle ON di default. Numeri di backtest storici (SAL.md) sono superati: non citarli.

### Verifica
Aprire il grafico e abilitare la strategia; nessuna verifica automatica nel repo. `wc -l *.pine` (v8.2 MINIMAL = 122 righe).

### Problemi noti
- SAL.md in `docs/archivio/` cita numeri non riconducibili al codice: non fidarsi.

## backtest

### Requisiti
Python 3. Dipendenze realmente importate dal codice (`backtest/src/*.py`): `yfinance` (solo `download_data.py`, riga 5), `pandas`, `numpy`; il resto è stdlib o moduli del repo. Nessun `requirements.txt` nel repo: le versioni usate non sono registrate (non verificato, installare manualmente).

### Installazione
```bash
cd backtest
pip install yfinance pandas numpy
```
Versioni: non registrate nel repo; non indicate qui.

### Avvio
```bash
python3 backtest/src/download_data.py     # rete richiesta (Yahoo Finance)
python3 backtest/src/check_data.py
python3 backtest/src/run_baseline.py
```
Cartella di lancio: radice del repo (percorsi `backtest/src/...`). Nessun argomento da riga di comando (il codice non usa `sys.argv` né `argparse`). I percorsi di dati e report sono relativi al file (`DATA_DIR`), quindi funzionano anche da altra cartella. `download_data.py` (rete, Yahoo Finance) va eseguito per primo: `backtest/data/` manca nel worktree (gitignored).

### Uso
- `download_data.py`: **rete** (yfinance, `yf.download` righe 18-25). Scarica OHLCV di SPY/QQQ/IWM (riga 9): 4h con `period=729d` salvato come `backtest/data/<TK>_240m.csv`, 1d con `period=10y` salvato come `<TK>_1d.csv` (righe 11-14, 43-44). Colonne open/high/low/close/volume, `auto_adjust=True`. Nessun argomento CLI; stampa un riepilogo.
- `check_data.py`: legge tutti `backtest/data/*.csv` (righe 10, 52) e stampa una tabella per file. Controlli come da docstring (riga 1); il corpo di `check_one` non è stato riletto nel dettaglio. Nessuna rete.
- `run_baseline.py`: backtest baseline v6.4 (SPY/QQQ/IWM, 240m e 1d). Legge `backtest/data/<TK>_<tf>.csv` e `<TK>_1d.csv` per il filtro daily (righe 26-27; TICKERS riga 15, TF_LABELS riga 16). Scrive `backtest/reports/baseline.csv` (righe 62-64). Nessuna rete, nessun argomento CLI.
- `run_atr_baseline.py`: baseline ATR-adaptive
- `optimize.py`: grid search ATR multiplier (train/test 70/30)
- `global_optimize.py`: un set ATR globale per tutti gli strumenti. `INSTRUMENTS` (righe 26-33): 6 coppie ticker/tf, 240m con 3 fold e 1d con 5. Legge dati da `backtest/data/` (righe 37-38). Scrive `backtest/reports/global_sweep.csv` (riga 114) e `global_top.csv` (riga 122). Nessuna rete, nessun argomento CLI.
- `walk_forward.py`: walk-forward K fold su SPY/QQQ/IWM, 240m con k=3 e 1d con k=5 (righe 189-190). Legge `backtest/data/` (righe 142-143, `load_csv` riga 68). Scrive `backtest/reports/wf_sweep_<TK>_<tf>.csv` (riga 165), `wf_top_<TK>_<tf>.csv` (riga 176) e `wf_summary.csv` (riga 217). Nessuna rete, nessun argomento CLI.
- `compare_baseline_vs_optimized.py`: confronto baseline v6.4 (% fisse) vs parametri ATR ottimizzati (TICKERS riga 25, TF_LABELS riga 26; dati righe 56-57). Scrive `backtest/reports/comparison.csv` (riga 82) e stampa il delta. Nessuna rete, nessun argomento CLI.
- `backtest_engine.py`, `strategy.py`, `metrics.py`, `pine_ta.py`: libreria (import nel codice, non eseguibile singolarmente)

### Verifica
`bash tools/py-gate.sh .` → "Sintassi python: tutti i .py compilano (13 file)", exit 0 (verificato).
Non eseguito (rete): `download_data.py`. Non eseguito (rete/dati, `backtest/data/` assente): `check_data.py`, `run_baseline.py`, `global_optimize.py`, `walk_forward.py`, `compare_baseline_vs_optimized.py`. Install pip: non verificato.

### Problemi noti
- Dipendenza da yfinance (rete): senza rete nessun backtest eseguibile.
- Nessun requirements.txt nel repo: versioni delle dipendenze non registrate (la versione usata non è tracciata).

## py-gate.sh

### Requisiti
Bash, Python 3.

### Installazione
Nessuna.

### Avvio
```bash
bash tools/py-gate.sh .
```

### Uso
Compila ogni `.py` tracciato; exit 0 se tutti compilano, 1 se almeno uno fallisce, 2 se perimetro non giudicabile.

### Verifica
Eseguito: "Sintassi python: tutti i .py compilano (13 file)", exit 0.

### Problemi noti
Nessuno.
