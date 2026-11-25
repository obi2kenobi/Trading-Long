# Bug — M-031.73b.2 (G4)

## BUG-1
Dove: backtest/src/pine_ta.py (supertrend, up/dn banding)
Gravità: media
Prova: letto codice — condizioni invertite: up band usava `prev_close > prev_up` (dovrebbe `> prev_dn`), dn band `prev_close < prev_dn` (dovrebbe `< prev_up`). Runtime non disponibile (pandas assente); riproduzione statica.
Correzione: ac35100 — `up[i] = max(upc_v[i], prev_up) if prev_close > prev_dn`; `dn[i] = min(dnc_v[i], prev_dn) if prev_close < prev_up`.
Test: py_compile OK; test repo non peggiorati (nessun test affidabile installato).

## BUG-2
Dove: backtest/src/backtest_engine.py (TP1/TP2, partial close)
Gravità: media
Prova: grep confermato — `p.tp1_qty`/`p.tp2_qty` definiti in strategy.py:77,79 e non letti; hardcoded `qty * 0.30`.
Correzione: 2ff0b16 — `partial = qty * (p.tp1_qty / 100.0)` e `partial = qty * (p.tp2_qty / 100.0)`.
Test: py_compile OK.

## Non fatto
CANDIDATO-3 (metrics.py profit_factor su pnl_perc) — fuori perimetro (solo CANDIDATO-1 e CANDIDATO-2 richiesti).
