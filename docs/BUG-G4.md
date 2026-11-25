# Bug candidati — M-031.73b.1 (G4)

CANDIDATO-1: backtest/src/pine_ta.py:124-125 — logica supertrend errata: le condizioni usate per aggiornare up/dn band sono invertite (up band usa `prev_close > prev_up` invece di `prev_close > prev_dn`; dn band usa `prev_close < prev_dn` invece di `prev_close < prev_up`). Falsa perdita/corruzione dei livelli di trend e del trend sign.

CANDIDATO-2: backtest/src/backtest_engine.py:231,242 — TP1/TP2 chiudono hardcoded il 30% della posizione residua (`qty * 0.30`) invece di usare `p.tp1_qty`/`p.tp2_qty` (definiti in strategy.py:77,79 e non letti da nessun'altra parte). Parametri ignorati in silenzio → profitto/perdite sbagliate se si modifica il qty.

CANDIDATO-3: backtest/src/metrics.py:73-76 — profit_factor è calcolato sui pnl percentuali dei trade (`pnls = [t.pnl_perc]`) anziché su PnL assoluti; con capitali parziali per trade diversi il profit factor è distorto. (minore, ma logica errata in rapporto)

## Rapporto
- CANDIDATO-1: riproduzione — letto codice; nessuna correzione. Causa: falso ramo di aggiornamento delle bande supertrend (condizioni su prev_up/prev_dn invertite), conseguente trend sign e TP/SL errati.
- CANDIDATO-2: riproduzione — grep confermato: tp1_qty/tp2_qty non letti. Causa: hardcoded 0.30 nei due punti.
- CANDIDATO-3: riproduzione — grep metrics.py confermato. Causa: uso di pnl_perc invece di pnl_abs (Trade.pnl_abs esiste e non viene usato per pf).
