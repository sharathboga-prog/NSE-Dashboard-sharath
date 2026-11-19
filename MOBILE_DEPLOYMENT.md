# NSE Quant — use on your phone

## Immediate mobile use

Download `mobile_dashboard.html` to your phone and open it in Chrome or Safari. The standalone HTML contains all CSS and JavaScript. It has interactive tabs, OHLCV CSV import, scanner filters, red/green candlestick charts with SMA 6/30, a VIX-adjusted risk calculator, and a downloadable master summary. It saves imported prices to browser local storage, where supported. Some in-app file previews disable JavaScript or local storage; use the phone's full browser if necessary.

**The standalone mobile HTML does not automatically fetch live quotes.** Upload verified daily OHLCV CSV, or deploy the Python Streamlit app for internet-connected public feeds. Market-context figures displayed in the HTML are dated historical reports.

## Public mobile URL and home-screen shortcut

Upload `mobile_dashboard.html`, `manifest.webmanifest`, and `sw.js` to an HTTPS static host (GitHub Pages, Cloudflare Pages, Netlify). On GitHub Pages: create a repository, upload these files, enable Pages under Settings > Pages, deploy from the main branch, then open the published `/mobile_dashboard.html` URL in your phone browser. Choose Add to Home Screen to create a shortcut. A public link does not exist until the files are deployed.

For live internet-connected market feeds, deploy `app.py` with `analytics.py`, `data_sources.py`, `requirements.txt`, and `.streamlit/config.toml` on Streamlit Community Cloud (or another Python host). Streamlit produces a mobile-accessible HTTPS URL. Feed availability is not guaranteed and 30-second UI refresh is not a guarantee of live quotes. Never upload credential files or tokens to a public repo.

## CSV import format

Headers: `symbol,date,open,high,low,close,volume` with optional `benchmark_close` (for NIFTY beta). Dates use `YYYY-MM-DD`; include at least 35 trading sessions per symbol for trade planning and 60 paired returns for beta. This dashboard never places trades.
