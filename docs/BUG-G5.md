# BUG-G5 — bug gravi trovati nel backtest (M-032.73b)

Scope: backtest/src/backtest_engine.py. Riproduzione: /tmp/m032b/repro.py (fuori repo, numpy 2.5.5 / pandas 3.1.1 da /tmp/m032b-venv).
Test del repo: nessuna suite automatica presente; gate di sintassi `bash tools/py-gate.sh .` eseguito prima e dopo (verde in entrambi i casi).

## BUG-1 — ATR di entrata letta dalla barra di fill (look-ahead)

Dove: backtest/src/backtest_engine.py:163 (originale riga 161)
Gravità: alta. Look-ahead nello stop di entrata: attivo con use_atr_targets=True (optimize, walk_forward, run_atr_baseline, compare); distorce i risultati ottimizzati.
Prova: repro.py prima → `BUG1 SL fills: []` ENTRY 100.05, SL atteso ~98.5 con ATR del segnale 1.0. Lo stop era calcolato con ATR 5.0 della barra di fill (SL 92.5), quindi il low 98 non lo toccava.
Correzione: e6263f9 (ATR letta da atr_in[i-1], barra di segnale; NaN → 0.0 come prima)
Test: repro.py dopo → `BUG1 SL fills: [('SL', 98.5)]`. Esito: OK. Gate sintassi: verde.

## BUG-2 — tp1_qty / tp2_qty ignorati (quantità TP hardcoded al 30%)

Dove: backtest/src/backtest_engine.py:233 e :244 (originali 231 e 242); parametri in backtest/src/strategy.py:77-79
Gravità: media. I parametri tp1_qty/tp2_qty erano definiti ma mai letti: lo sweep su quei parametri non aveva effetto e i risultati dei test di sensibilità erano falsi.
Prova: repro.py prima → `BUG2 TP1 qty/entry: 0.3` con tp1_qty=50 (atteso 0.5).
Correzione: 2323247 (qty * tp1_qty/100 e qty * tp2_qty/100, con clamp 0–100; default 30 invariato)
Test: repro.py dopo → `BUG2 TP1 qty/entry: 0.5`. Esito: OK. Gate sintassi: verde.

## BUG-3 — posizione aperta a fine dati mai chiusa né registrata

Dove: backtest/src/backtest_engine.py:286-299 (dopo il loop principale; originale fine ciclo righe 275-283)
Gravità: alta. Una posizione aperta alla fine dei dati usciva dal conteggio trades: n_trades, win rate e profit factor erano distorti e l'equity finale non includeva la chiusura.
Prova: repro.py prima → `BUG3 trades: 0 | fills: ['ENTRY']` (atteso 1 trade chiuso a fine dati).
Correzione: f0208d4 (chiusura a mercato al close dell'ultima barra con slippage e commissioni, exit_reason=EOD, fill EOD, equity finale aggiornata)
Test: repro.py dopo → `BUG3 trades: 1 | fills: ['ENTRY', 'EOD']`. Esito: OK. Gate sintassi: verde.
