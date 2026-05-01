# SAL — Ottimizzazione TEMA-ST-WT LONG

**Data:** 2026-05-01
**Branch:** `claude/review-script-work-OqTza`
**Stato:** ✅ Completato — Pine v6.5 pronto al test su TradingView

---

## 1. Obiettivo

Migliorare la strategia `TEMA-ST-WT LONG OPT.pine` (v6.4) rendendola **più sicura** (drawdown↓) e **più profittevole**, validando le modifiche con dati reali di Yahoo Finance su SPY, QQQ e IWM su timeframe 240m e 1d.

**Priorità metriche concordate con utente:**
1. Max Drawdown ↓
2. Sharpe Ratio ↑
3. Profit Factor ↑
4. Net Profit ↑
5. Win Rate (informativo)

---

## 2. Cosa è stato fatto

### 2.1 Infrastruttura backtest in Python (`/backtest/`)
- **Download dati** Yahoo Finance: SPY/QQQ/IWM × 4h(~3y) + 1d(10y), 6 dataset puliti
- **Port Python 1:1** della strategia v6.4 (TEMA, Supertrend, WaveTrend, RSI, ATR, ADX, filtri scoring, 3-level TP, trailing, cooldown)
- **Engine bar-by-bar** che replica la semantica Pine: signal-at-close → fill-at-next-open, SL priority over TP, partial exits TP1/TP2/TP3
- **Allineamento HTF Daily senza look-ahead** per i backtest 4h
- **Metrics**: Sharpe, Sortino, Max DD (incl. durata), PF, win rate, CAGR

### 2.2 Baseline v6.4 (parametri originali)
La strategia funzionava bene su SPY ma falliva su instrumenti più volatili:

| Ticker | TF | PF | Ret% | Sharpe | MaxDD% |
|---|---|---|---|---|---|
| SPY | 240m | 2.50 | +31 | 1.25 | -8 |
| SPY | 1d | 1.99 | +78 | 0.83 | -11 |
| QQQ | 240m | **0.94** | -0.1 | 0.04 | -20 |
| QQQ | 1d | 2.22 | +137 | 1.07 | -10 |
| IWM | 240m | **0.87** | -6 | -0.16 | -16 |
| IWM | 1d | **0.95** | -8 | -0.06 | -24 |

3 strumenti con PF<1 → strategia tarata su SPY, non scalava per volatilità diverse.

### 2.3 Aggiunta modalità ATR-adattiva
Estesa la strategia con SL/TP/Trailing **multipli dell'ATR catturato all'entry** (non ricomputato barra-per-barra). Toggle `use_atr_targets`. Il vecchio comportamento fixed-% rimane disponibile e identico (regression OK).

### 2.4 Walk-forward optimization
- Spazio: 168 combinazioni vincolate (sl/tp1/tp2/tp3/trail × ATR multipliers)
- **Cross-validation**: 24 fold disgiunti totali (3 fold su 4h, 5 su 1d) × 6 strumenti
- Eligibilità: PF≥1.2, mean DD≥-15%, min Sharpe>-0.5
- Selezione: massimo mean Sharpe → poi tie-break su worst-case DD

**Set scelto** (singolo, robusto cross-instrument):
```
SL  = 1.5 × ATR
TP1 = 1.5 × ATR  (chiude 30%)
TP2 = 5.0 × ATR  (chiude 30% del rimanente)
TP3 = 8.0 × ATR  (chiude resto)
Trailing arm @ profit = 3.0 × ATR
Trailing offset = 0.5 × ATR (BE+0.5×ATR)
```

### 2.5 Confronto v6.4 vs v6.5 ATR-ottimizzato (full-period)

| Ticker | TF | PF v6.4→v6.5 | Ret% v6.4→v6.5 | Sharpe v6.4→v6.5 | DD% v6.4→v6.5 |
|---|---|---|---|---|---|
| SPY | 240m | 2.50→2.33 | +31→+26 | 1.25→**1.27** | -8.0→**-7.2** |
| SPY | 1d | 1.99→**2.38** | +78→**+88** | 0.83→**0.87** | **-10.9**→-13.8 |
| QQQ | 240m | 0.94→**1.38** | -0→**+15** | 0.04→**0.62** | -20.5→**-15.1** |
| QQQ | 1d | 2.22→**2.51** | +137→**+160** | **1.07**→1.04 | **-9.5**→-16.4 |
| IWM | 240m | 0.87→**1.04** | -6→**+8** | -0.16→**0.31** | -15.8→**-11.2** |
| IWM | 1d | 0.95→**1.83** | -8→**+76** | -0.06→**0.59** | -24.4→**-18.8** |
| **MEDIA** | | **1.58→1.91** | **+39→+59** | **0.50→0.78** | **-14.8→-13.8** |

**Risultato aggregato:**
- ✅ I 3 strumenti perdenti diventano profittevoli
- ✅ Sharpe medio +56% (0.50 → 0.78)
- ✅ PF medio +21% (1.58 → 1.91)
- ✅ Worst-case DD migliora (-24.4% → -18.8%)
- ⚠️ Trade-off accettato: SPY 1d e QQQ 1d hanno DD leggermente peggiore (≈+3-7 pt) — è il prezzo della robustezza cross-asset

### 2.6 Applicazione al Pine Script (v6.5)
File `TEMA-ST-WT LONG OPT.pine` aggiornato:
- Header e `strategy(...)` → v6.5
- Nuovo gruppo input "🎯 ATR-Adaptive Targets v6.5" con 7 parametri
- Toggle `useATRTargets` (default ON, OFF = comportamento v6.4 invariato)
- `var float entryATR = na`, catturato al momento dell'entry come `entryATR := atr_in`
- SL/TP1/TP2/TP3/Trailing usano `entryATR × multiplier` quando il toggle è ON
- Labels e comment delle exit aggiornati per mostrare i target in formato `N×ATR`

---

## 3. Struttura del progetto

```
/home/user/Trading-Long/
├── TEMA-ST-WT LONG OPT.pine         # ⭐ Strategy v6.5 (deploy su TradingView)
├── CLAUDE.md                          # Regole di lavoro
├── SAL.md                             # questo documento
└── backtest/
    ├── data/                          # CSV Yahoo Finance (gitignored, rigenerabili)
    ├── reports/                       # Output dei backtest (CSV)
    │   ├── baseline.csv               # v6.4 default, full-period
    │   ├── atr_baseline.csv           # ATR con multiplier ingenui
    │   ├── comparison.csv             # ⭐ confronto v6.4 vs v6.5 ottimizzato
    │   ├── global_top.csv             # top 15 set globali da walk-forward
    │   ├── wf_summary.csv             # best per (ticker, tf)
    │   ├── wf_sweep_*.csv             # sweep completo per ogni ticker/tf
    │   └── wf_top_*.csv               # top 10 per ogni ticker/tf
    └── src/
        ├── pine_ta.py                 # ema/rma/rsi/atr/dmi/supertrend/wavetrend
        ├── strategy.py                # StrategyParams + signal computation
        ├── backtest_engine.py         # bar-by-bar simulator (TP/SL/trailing/cooldown)
        ├── metrics.py                 # Sharpe, MaxDD, PF, ecc.
        ├── download_data.py           # download Yahoo Finance
        ├── check_data.py              # sanity check OHLCV
        ├── run_baseline.py            # baseline v6.4
        ├── run_atr_baseline.py        # ATR mode con multiplier ingenui
        ├── optimize.py                # grid search 70/30 train/test
        ├── walk_forward.py            # walk-forward per (ticker, tf)
        ├── global_optimize.py         # walk-forward globale (24 fold pool)
        └── compare_baseline_vs_optimized.py  # ⭐ tabella finale
```

---

## 4. Come riprodurre tutto

```bash
# 1) Setup (una volta)
pip install yfinance pandas numpy

# 2) Download dati (genera /backtest/data/*.csv)
cd backtest && python3 src/download_data.py

# 3) Verifica integrità dati
python3 src/check_data.py

# 4) Baseline v6.4
python3 src/run_baseline.py

# 5) Walk-forward globale (~25s, 168 combo × 24 fold)
python3 src/global_optimize.py

# 6) Confronto finale v6.4 vs v6.5
python3 src/compare_baseline_vs_optimized.py
```

---

## 5. Possibili prossimi passi (NON FATTI, da valutare)

1. **Backtest v6.5 reale su TradingView** — il Python è una replica accurata ma non identica al 100% (es. ordering intra-bar di SL e TP). Confermare i numeri sul backtester ufficiale.
2. **Ottimizzare anche i filtri**: `min_filters_required`, `rsi_overbought`, `adx_threshold` non sono stati toccati. Margine di miglioramento potenziale ulteriore.
3. **Regime-switching**: parametri ATR diversi in base a `volRegime` (high/normal/low). Più complesso, da valutare.
4. **Walk-forward a 5+ fold per ticker** invece di 3 sui 4h (richiede più dati o test futuri).
5. **Estendere a futures/forex/crypto** — il design ATR-based dovrebbe generalizzare bene.
6. **Aggiungere short side** (oggi è long-only).

---

## 6. Note operative

- **Modalità ATR ON di default in v6.5**: per tornare a v6.4 esatto, basta togliere il flag `🎯 Usa Target ATR-Adattivi`.
- **Min ATR consigliato**: usare timeframe con almeno 14 barre prima del primo entry (warmup ATR).
- **Slippage 0.05% e commission 0.01%** già modellati nel backtest. In live, la commissione reale del broker può differire.
- **Il backtest Python NON modella**: gap notturni multi-bar (assume open di sessione), short-locate fees, dividendi (auto_adjust=True quindi prezzi rettificati per dividendi).

---

**Riferimenti commit principali sul branch `claude/review-script-work-OqTza`:**
- `chore: add backtest scaffolding ...` — download + check dati
- `feat: add Python port of TEMA-ST-WT v6.4 ...` — engine + baseline
- `feat: add ATR-adaptive SL/TP mode ...` — modalità ATR
- `feat: add grid-search optimization ...` — train/test 70/30
- `feat: add walk-forward + global optimization ...` — ⭐ scelta finale parametri v6.5
