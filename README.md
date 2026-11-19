## NIFTY 500 full-universe scanner

Select **All NIFTY 500 (batch scan)** in the Streamlit sidebar. Load the official NSE Indices constituent CSV and scan in batches (10–50 symbols per click). Coverage and failures are displayed; scans are cached in the current Streamlit session. All 500 members must be successfully scanned before claiming complete coverage. Source: https://www.niftyindices.com/indices/equity/broad-based-indices/NIFTY-500 . Public quote feeds can throttle/block bulk requests. The offline mobile HTML accepts a verified multi-symbol OHLCV CSV for all 500 but cannot fetch market prices by itself.

## Mobile interactive dashboard

`mobile_dashboard.html` is a self-contained phone-friendly dashboard with CSV scanner, red/green candlestick charts, SMA6/30, VIX sizing and CSV export. See `MOBILE_DEPLOYMENT.md` for opening on a phone and hosting on an HTTPS URL. Static HTML does not auto-fetch quotes.

# NSE Quant Dashboard — working independent project

A read-only Streamlit dashboard for NSE swing-trading research. It does **not** modify or claim to restore an inaccessible prior Codex project. No broker connectivity, credentials, or order submission is implemented.

## Start on Windows / macOS / Linux

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local address shown by Streamlit (normally http://localhost:8501). Internet connectivity is required for live public feeds. If Yahoo Finance/NSE blocks or delays requests, the dashboard marks those fields as missing; it does not invent quotes.

## Included

- NSE watchlist scanner (CSV upload or symbols), 6/30 SMA, RSI14, ATR14, 20-day volume, breakout, 5-day crossover flags.
- Red/green daily candlesticks, SMA6 gold, SMA30 blue, support/resistance and hypothetical entry/stop/targets.
- Risk-budget sizing adjusted for India VIX with source and timestamp, plus exchange-lot rounding for verified F&O futures contract sizes. **Do not use underlying sizing for options**.
- Conviction Low / Medium / High / Very High using transparent conditions (not calibrated probability).
- NIFTY beta using up to 252 paired daily return observations, minimum 60.
- NSE provisional FII/DII feed where accessible, official-link fallback, CSV upload; sector/global proxy performance; Moneycontrol headlines via Google News RSS; economic event CSV; technical avoid flags.
- Master table CSV export, missing-data status, source timestamps, risk rules, optional fundamentals on demand.
- Optional 30-second **UI refresh**; network fetches are cached 10–30 minutes. No guarantee of 30-second exchange quotes.

## Data provenance and caveats

- Stock, index and VIX historical OHLCV: Yahoo Finance (via `yfinance`), *not* an exchange-authoritative execution feed. The application records the last available trading session.
- FII/DII: official NSE provisional cash-market API (may reject automated access), plus user-uploaded exchange reports. Check NSE-only vs combined scope.
- News: Google News RSS headlines filtered to Moneycontrol articles, linking to reporting; not a licensed Moneycontrol data API.
- Historical snapshot `snapshot_2026-11-19.json` contains a small number of source-verified **dated** contextual facts, not real-time prices.
- F&O lot sizes: no hardcoded lot sizes. Upload the relevant exchange contract data after verifying it. See `sample_data/fno_lot_sizes_TEMPLATE.csv`.
- Economic events: no invented dates. Upload sourced calendar via `sample_data/economic_events_TEMPLATE.csv`.
- Conviction score is a deterministic rule-count heuristic; not a probability or recommendation.
- Price planning uses breakout entry = max(last close, prior 20-day high) × 1.002; stop = min(prior 10-day low, entry − 1.5 × ATR14); targets = 1.5R and 2.5R. Confirm with current liquidity/quotes and risk controls.
- Risk size is **not** margin or total exposure control. The base calculation ignores fees, slippage, gaps, leverage and liquidity.

## Tests

```bash
pytest -q
```

## Important: existing Codex project

The original `nse_quant_dashboard.zip` or its files are not available to this runtime. To merge these features into the *existing* dashboard without losing its prior OI/MWPL, option-chain, watchlist, and scanner functionality, provide the existing project ZIP or open the existing project in ChatGPT Work mode. This standalone project deliberately does not claim those earlier components are migrated.
