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
Python 3; dipendenze `yfinance`, `pandas`, `numpy` (non pinnate, installare manualmente).

### Installazione
```bash
cd backtest
pip install yfinance pandas numpy
```

### Avvio
```bash
python3 backtest/src/download_data.py     # rete richiesta (Yahoo Finance)
python3 backtest/src/check_data.py
python3 backtest/src/run_baseline.py
```

### Uso
- `download_data.py`: scarica OHLCV SPY/QQQ/IWM a 240m e 1d in `backtest/data/` (gitignored)
- `check_data.py`: sanity check dati (duplicati, gap, NaN, volume)
- `run_baseline.py`: backtest baseline v6.4 (SPY/QQQ/IWM, 4h e 1d)
- `run_atr_baseline.py`: baseline ATR-adaptive
- `optimize.py`: grid search ATR multiplier (train/test 70/30)
- `global_optimize.py`: un set ATR globale per tutti gli strumenti
- `walk_forward.py`: walk-forward K fold
- `compare_baseline_vs_optimized.py`: confronto baseline vs ottimizzato
- `backtest_engine.py`, `strategy.py`, `metrics.py`, `pine_ta.py`: libreria (import nel codice, non eseguibile singolarmente)

### Verifica
`bash tools/py-gate.sh .` → "Sintassi python: tutti i .py compilano (13 file)", exit 0 (verificato).
Gli altri comandi richiedono rete/dati: **non verificati**.

### Problemi noti
- Dipendenza da yfinance (rete): senza rete nessun backtest eseguibile.
- Nessun requirements.txt nel repo.

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
