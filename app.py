"""NSE Quant Dashboard — independent, read-only Streamlit project.

Not a replacement for inaccessible prior project files. No broker credentials or order endpoints.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from analytics import indicators, beta_to_benchmark, conviction, safe_float, size_trade, trade_setup
from data_sources import fetch_yahoo, fetch_fundamentals, fetch_nse_fii_dii, fetch_moneycontrol_headlines, now_utc
from nifty500 import fetch_constituents

BASE = Path(__file__).parent
IST = ZoneInfo("Asia/Kolkata")
DEFAULT = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "LT", "SBIN", "BHARTIARTL"]
SECTORS = {"Bank": "^NSEBANK", "IT": "^CNXIT", "Pharma": "^CNXPHARMA", "Auto": "^CNXAUTO", "Metal": "^CNXMETAL", "FMCG": "^CNXFMCG", "Energy": "^CNXENERGY"}
GLOBAL = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow Jones": "^DJI", "Nikkei 225": "^N225", "Hang Seng": "^HSI", "Brent crude": "BZ=F", "USD/INR": "INR=X"}

st.set_page_config(page_title="NSE Quant | Trading Intelligence", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
st.markdown('''<style>
.block-container{padding-top:1.4rem;max-width:1600px}
[data-testid="stMetric"]{background:#151f33;border:1px solid #263755;padding:12px 15px;border-radius:12px}
[data-testid="stMetricLabel"]{color:#a8b7d2}
.hero{padding:22px 26px;border-radius:18px;background:linear-gradient(110deg,#1c2b55,#111b30);border:1px solid #34466d;margin-bottom:15px}
.hero h1{font-size:2.0rem;margin:0;color:#f4f7ff}
.hero p{margin:6px 0 0;color:#b6c6e4}
.note{padding:12px 15px;border:1px solid #344362;background:#17233a;border-radius:10px;color:#c4d4ef}
.small{font-size:12px;color:#a6b7d2}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=600, show_spinner=False)
def prices(symbol: str):
    try:
        return indicators(fetch_yahoo(symbol, "18mo")), None
    except Exception as exc:
        return pd.DataFrame(), f"{symbol}: {str(exc)[:160]}"

@st.cache_data(ttl=3600, show_spinner=False)
def fundamentals(symbol):
    try:
        return fetch_fundamentals(symbol), None
    except Exception as exc:
        return {}, str(exc)[:160]

@st.cache_data(ttl=900, show_spinner=False)
def flows():
    try:
        return fetch_nse_fii_dii()[0], None
    except Exception as exc:
        return pd.DataFrame(), str(exc)[:160]

@st.cache_data(ttl=1800, show_spinner=False)
def news():
    try:
        return fetch_moneycontrol_headlines()[0], None
    except Exception as exc:
        return pd.DataFrame(), str(exc)[:160]


def last_dt(df):
    if df.empty:
        return "Unavailable"
    d=df.index[-1]
    if hasattr(d, 'tz') and d.tz is not None:
        d=d.tz_convert(IST)
    return str(d)[:19] + " IST" if getattr(d,'tz',None) is not None else str(d)[:10] + " (daily session date)"


def pct_return(df, n):
    if len(df) <= n: return None
    a=safe_float(df['Close'].iloc[-1]); b=safe_float(df['Close'].iloc[-1-n])
    return 100*(a/b-1) if a is not None and b is not None and b > 0 else None


def fmt(v, digits=2, suffix=""):
    x=safe_float(v)
    return f"{x:,.{digits}f}{suffix}" if x is not None else "Pending"


def chart(df, sym, setup):
    view=df.tail(150)
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.04,row_heights=[.76,.24])
    fig.add_trace(go.Candlestick(x=view.index,open=view.Open,high=view.High,low=view.Low,close=view.Close,
                                 increasing_line_color="#23c88d",decreasing_line_color="#ff6476",name="Candles"),row=1,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view.SMA6,name="SMA 6",line=dict(color="#f9bc59",width=2)),row=1,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view.SMA30,name="SMA 30",line=dict(color="#5b9aff",width=2)),row=1,col=1)
    crosses=view[view.BullCross.fillna(False)]
    if not crosses.empty:
        fig.add_trace(go.Scatter(x=crosses.index,y=crosses.Low*.99,mode="markers",name="Bull crossover",marker=dict(color="#3ee6b5",size=12,symbol="triangle-up")),row=1,col=1)
    if setup.get('status') == 'Planning only':
        for label,key,color in [("Entry",'entry','#a6c9ff'),('Stop','stop','#ff6476'),('Target 1','target1','#41d6a4'),('Target 2','target2','#71e9c1'),('Support','support','#a685e6'),('Resistance','resistance','#d6a865')]:
            fig.add_hline(y=setup[key],line_color=color,line_dash="dash",line_width=1,annotation_text=f"{label} ₹{setup[key]}",annotation_position="top left",row=1,col=1)
    fig.add_trace(go.Bar(x=view.index,y=view.Volume,name="Volume",marker_color="#556f9e"),row=2,col=1)
    fig.update_layout(height=590,template="plotly_dark",paper_bgcolor="#0c1221",plot_bgcolor="#10192b",margin=dict(l=10,r=15,t=30,b=10),
                      title=f"{sym} • Daily candlesticks • SMA 6/30",xaxis_rangeslider_visible=False,legend=dict(orientation="h",y=1.06,x=0))
    return fig

snapshot=json.loads((BASE/'snapshot_2026-11-19.json').read_text(encoding='utf-8'))
st.markdown('<div class="hero"><h1>NSE QUANT • MARKET INTELLIGENCE</h1><p>Read-only swing scanner · Daily candles · SMA 6/30 · India VIX sizing · Market intelligence · Source audit</p></div>',unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Dashboard controls")
    st.caption("All market feeds are read-only. Prices may be delayed. No orders are submitted.")
    universe_mode=st.radio("Scanner universe",["Custom watchlist", "All NIFTY 500 (batch scan)"],help="NIFTY 500 membership is loaded from official NSE Indices CSV. Scan in controlled batches to avoid public-feed rate limits.")
    input_symbols=st.text_area("NSE symbols (comma/newline separated)",", ".join(DEFAULT),height=100,disabled=universe_mode.startswith("All"))
    upload=st.file_uploader("Or upload watchlist CSV (symbol column)",type='csv',key='watch')
    raw=input_symbols.replace('\n',',').split(',')
    if upload is not None:
        try:
            u=pd.read_csv(upload)
            raw=u['symbol'].astype(str).tolist()
        except Exception as exc: st.error(f"Watchlist CSV error: {exc}")
    symbols=[]
    for x in raw:
        s=x.strip().upper().replace('.NS','')
        if s and s.replace('&','').replace('-','').isalnum() and s not in symbols: symbols.append(s)
    if universe_mode.startswith("All"):
        if st.button("Load official NIFTY 500 constituents",use_container_width=True):
            try:
                members,src=fetch_constituents()
                st.session_state['nifty500_members']=members
                st.session_state['nifty500_source']=src
                st.session_state['nifty500_results']={}
                st.session_state['nifty500_errors']={}
            except Exception as exc: st.error(f"Could not load official NIFTY 500 members: {exc}")
        members=st.session_state.get('nifty500_members',[])
        if members:
            st.caption(f"Official constituent universe: {len(members)} symbols · {st.session_state.get('nifty500_source','')}")
            batch_size=st.select_slider('Symbols per scan batch',options=[10,20,25,50],value=25)
            already=st.session_state.setdefault('nifty500_results',{})
            failed=st.session_state.setdefault('nifty500_errors',{})
            st.progress(len(already)/len(members),text=f"Completed: {len(already)}/{len(members)} · Failed: {len(failed)}")
            if st.button('Scan next batch',use_container_width=True,type='primary'):
                todo=[m for m in members if m not in already and m not in failed][:batch_size]
                progress=st.progress(0,text='Scanning daily OHLCV…')
                for i,sym in enumerate(todo):
                    df,err=prices(sym+'.NS')
                    if err or df.empty: failed[sym]=err or 'No OHLCV'
                    else: already[sym]=df
                    progress.progress((i+1)/len(todo),text=f"Scanned {i+1}/{len(todo)} in this batch")
                st.rerun()
            if st.button('Retry failed symbols',use_container_width=True):
                failed.clear();st.rerun()
            if st.button('Clear NIFTY 500 scan cache',use_container_width=True):
                st.session_state['nifty500_results']={};st.session_state['nifty500_errors']={};st.rerun()
            st.caption('Continue pressing Scan next batch until all members are covered. Incomplete or failed symbols are not treated as passed.')
        symbols=[]
    elif len(symbols)>30:
        st.warning('Custom watchlist limited to 30 symbols; select NIFTY 500 for full-universe batch scanning.')
        symbols=symbols[:30]
    capital=st.number_input("Trading capital (₹)",min_value=1000.0,value=100000.0,step=10000.0)
    risk_pct=st.slider("Max planned risk per trade (%)",0.1,3.0,1.0,0.1)
    st.divider()
    st.subheader("India VIX provenance")
    vix_source=st.radio("VIX input",["Fetch market feed", "Use verified 18-Nov-2026 close (stale)", "Manual (user supplied)"],index=0)
    manual_vix=None
    if vix_source.startswith('Manual'):
        manual_vix=st.number_input('User-supplied VIX value',min_value=1.0,max_value=150.0,value=15.0,step=.1)
        manual_vix_time=st.text_input('Source and timestamp (required)',value='',placeholder='e.g. NSE India, 2026-11-19 10:30 IST')
    baseline=st.number_input('VIX baseline (heuristic)',min_value=1.0,value=15.0,step=1.0)
    floor=st.slider('Minimum position multiplier',0.1,1.0,.5,.05)
    st.caption('Multiplier = max(floor, min(1, baseline / VIX)). This is a configurable risk heuristic, not a validated forecast.')
    lot_csv=st.file_uploader('Optional verified F&O lot-size CSV',type='csv',key='lots')
    lot_map={}
    if lot_csv is not None:
        try:
            ldf=pd.read_csv(lot_csv)
            needed={'symbol','lot_size','asof','source'}
            if not needed.issubset(ldf.columns): raise ValueError(f"Required columns: {', '.join(sorted(needed))}")
            for _,r in ldf.iterrows():
                if pd.notna(r['lot_size']) and pd.notna(r['source']) and pd.notna(r['asof']):
                    lot_map[str(r['symbol']).upper().replace('.NS','')] = int(r['lot_size'])
        except Exception as exc: st.error(f'F&O lot CSV error: {exc}')
    if st.button('↻ Force refresh market feeds',use_container_width=True):
        prices.clear(); fundamentals.clear(); flows.clear(); news.clear(); st.rerun()
    auto=st.toggle('Auto-refresh display every 30 seconds',value=False,help='Data requests are cached 10–30 minutes; a 30-second UI refresh does not mean 30-second fresh quotes.')
    if auto:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=30000,key='nse_autorefresh')
        except ImportError: st.warning('Install streamlit-autorefresh to enable timed UI refresh.')

now=datetime.now(IST)
st.caption(f"Viewed: {now:%d %b %Y %H:%M:%S} IST · Market data: Yahoo Finance via yfinance (delayed, not exchange-authoritative) · Cached up to 10 minutes")

with st.spinner('Loading available public market data…'):
    benchmark,benchmark_error=prices('^NSEI')
    vix_df,vix_error=prices('^INDIAVIX') if vix_source=='Fetch market feed' else (pd.DataFrame(),None)
    data={}; errors=[]
    if universe_mode.startswith('All'):
        data=dict(st.session_state.get('nifty500_results',{}))
        errors=[f"{sym}: {err}" for sym,err in st.session_state.get('nifty500_errors',{}).items()]
        symbols=st.session_state.get('nifty500_members',[])
    else:
        for sym in symbols:
            df,err=prices(sym+'.NS')
            if err: errors.append(err)
            if not df.empty: data[sym]=df

vix=None; vix_stamp='Missing'
if vix_source=='Fetch market feed' and not vix_df.empty:
    vix=safe_float(vix_df.Close.iloc[-1]); vix_stamp=f'Yahoo Finance ^INDIAVIX, {last_dt(vix_df)}'
elif vix_source.startswith('Use verified'):
    vix=15.56; vix_stamp='HDFC Sky, 18-Nov-2026 15:30 IST (STALE)'
elif vix_source.startswith('Manual') and manual_vix_time.strip():
    vix=manual_vix; vix_stamp='USER SUPPLIED: '+manual_vix_time.strip()

benchmark_up = (pct_return(benchmark,20) or 0)>0 if not benchmark.empty and pct_return(benchmark,20) is not None else None
rows=[]; avoided=[]; analyses={}
for sym,df in data.items():
    setup=trade_setup(df)
    level,score,pros,cons=conviction(df,benchmark_up)
    beta,nobs=beta_to_benchmark(df.Close,benchmark.Close) if not benchmark.empty else (None,0)
    latest=df.iloc[-1]
    lot=lot_map.get(sym)
    sizing=size_trade(capital,risk_pct,setup.get('entry'),setup.get('stop'),vix,baseline,floor,lot_size=lot) if setup.get('entry') else {'status':'Pending setup'}
    recent_cross=bool(df.BullCross.tail(5).fillna(False).any())
    trend='Bullish' if latest.SMA6>latest.SMA30 else 'Bearish'
    trade_status=('Watch — recent bullish cross' if recent_cross else 'Watch — bullish trend' if trend=='Bullish' else 'Avoid — bearish SMA trend')
    if level=='Pending' or setup.get('status')!='Planning only': trade_status='Pending data'
    if level in ('Low',) or trend=='Bearish':
        avoided.append({'Symbol':sym,'Reason':'; '.join(cons[:3]) or 'Weak technical setup','Data date':last_dt(df)})
    analyses[sym]=(df,setup,level,pros,cons,sizing)
    rows.append({'Symbol':sym,'Data as of':last_dt(df),'Close ₹':safe_float(latest.Close),
                 '5D %':pct_return(df,5),'20D %':pct_return(df,20),'SMA6 ₹':safe_float(latest.SMA6),
                 'SMA30 ₹':safe_float(latest.SMA30),'RSI14':safe_float(latest.RSI14),
                 'Volume x':safe_float(latest.VolRatio),'Recent 6/30 cross':recent_cross,
                 'Trend':trend,'Setup':'6/30 SMA + 20D breakout planning',
                 'Entry ₹':setup.get('entry'),'SL ₹':setup.get('stop'),'Target 1 ₹':setup.get('target1'),
                 'Target 2 ₹':setup.get('target2'),'R:R T1':setup.get('rr1'),'R:R T2':setup.get('rr2'),
                 'Beta vs NIFTY':beta,'Beta lookback':'252 sessions (min 60)','Beta observations':nobs,
                 'Conviction':level,'VIX multiplier':sizing.get('vix_factor'),
                 'Base units':sizing.get('base_units'),'Final units':sizing.get('final_units'),
                 'F&O lots':sizing.get('contracts'),'Exchange lot size':lot,
                 'Risk ₹':sizing.get('rupee_risk'),'Notional ₹':sizing.get('notional'),
                 'Risk status':sizing.get('status'),'Status':trade_status,
                 'Notes':'; '.join(cons[:2]) if cons else 'All observed rules passed',
                 'Price source':'Yahoo Finance via yfinance'})
master=pd.DataFrame(rows)

m1,m2,m3,m4,m5=st.columns(5)
m1.metric('Symbols with price data',f'{len(data)}/{len(symbols)}')
m2.metric('NIFTY 50',fmt(benchmark.Close.iloc[-1]) if not benchmark.empty else 'Pending',help=last_dt(benchmark))
m3.metric('India VIX',fmt(vix) if vix is not None else 'Pending',help=vix_stamp)
m4.metric('Recent SMA6/30 crosses',str(int(master['Recent 6/30 cross'].sum())) if not master.empty else 'Pending')
m5.metric('High / Very High',str(int(master.Conviction.isin(['High','Very High']).sum())) if not master.empty else 'Pending')

if vix is None:
    st.warning('India VIX is unavailable or unverified. VIX-adjusted quantities and rupee risk are marked PENDING, not estimated.')
elif 'STALE' in vix_stamp:
    st.warning('Using a dated VIX closing value only for illustrative sizing. Confirm current NSE VIX before acting.')
if errors:
    st.info(f'{len(errors)} stock feed(s) unavailable. See Data Quality for details.')

T=st.tabs(['📊 Overview','🕯️ Candlestick charts','🎯 Trade sizing','🌐 Market intelligence','📋 Master summary','🧾 Data quality','📐 Risk rules'])
with T[0]:
    a,b=st.columns([1.3,1])
    with a:
        st.subheader('Shortlist • technical scan')
        if master.empty: st.error('No live stock data. Check internet access or data-provider limits. No synthetic prices are substituted.')
        else:
            cols=['Symbol','Close ₹','5D %','SMA6 ₹','SMA30 ₹','RSI14','Volume x','Recent 6/30 cross','Conviction','Status']
            st.dataframe(master[cols].sort_values(['Recent 6/30 cross','5D %'],ascending=[False,False]),use_container_width=True,hide_index=True)
    with b:
        st.subheader('Verified reporting snapshot')
        st.caption('Historical context only; dates are not synchronized with live feeds.')
        for item in snapshot['verified_context']:
            st.markdown(f"**{item['topic']}** — {item['value']}  ")
            st.caption(f"{item['date']} · {item['source']} · {item['caveat']}")
            st.link_button(f"Source: {item['source']}",item['url'],use_container_width=False)
    st.subheader('Market breadth / setup quality')
    if not master.empty:
        c1,c2=st.columns(2)
        with c1:
            st.bar_chart(master.set_index('Symbol')['5D %'].dropna(),horizontal=True)
        with c2:
            st.bar_chart(master.groupby('Conviction').size())

with T[1]:
    if not data: st.warning('No OHLCV data available for candlestick charts.')
    else:
        selected=st.selectbox('Select NSE stock',list(data.keys()))
        df,setup,level,pros,cons,sizing=analyses[selected]
        st.plotly_chart(chart(df,selected,setup),use_container_width=True)
        c1,c2,c3,c4=st.columns(4)
        c1.metric('Entry planning level',f"₹{fmt(setup.get('entry'))}")
        c2.metric('Stop planning level',f"₹{fmt(setup.get('stop'))}")
        c3.metric('Target 1',f"₹{fmt(setup.get('target1'))}")
        c4.metric('Target 1 R:R',fmt(setup.get('rr1')))
        st.caption('Chart lines are rule-derived planning levels based on historical bars, not orders or verified executable quotes. Markers indicate completed daily 6/30 crossovers.')
        st.markdown('**Conviction evidence:** '+(', '.join(pros) if pros else 'None'))
        st.markdown('**Unmet conditions:** '+(', '.join(cons) if cons else 'None'))
        st.link_button('Check market reporting on Moneycontrol','https://www.moneycontrol.com/stocksmarketsindia/')

with T[2]:
    st.subheader('Risk-based size after India VIX adjustment')
    st.markdown(f"**VIX source:** {vix_stamp}. **Risk budget:** ₹{capital*risk_pct/100:,.2f} ({risk_pct:.1f}% of capital). **Baseline:** {baseline:g}; **floor:** {floor:.2f}.")
    if not master.empty:
        st.dataframe(master[['Symbol','Entry ₹','SL ₹','Base units','VIX multiplier','Final units','Exchange lot size','F&O lots','Risk ₹','Notional ₹','Risk status']],use_container_width=True,hide_index=True)
    st.info('For NSE futures, lot sizes must be verified against the relevant exchange contract file and uploaded. Final contracts = floor(adjusted underlying units / exchange lot size). Options require premium, strike, expiry, delta and scenario-based risk; underlying-share sizing is not valid for options.')
    st.code('base_units = floor((capital × risk_pct / 100) / (entry − stop))\nvix_factor = max(floor_factor, min(1, baseline_vix / current_vix))\nadjusted_units = floor(base_units × vix_factor)\nfutures_contracts = floor(adjusted_units / NSE_contract_lot_size)\nfinal_underlying_units = futures_contracts × NSE_contract_lot_size\nrupee_risk = final_underlying_units × (entry − stop)',language='python')
    st.caption('No margin, liquidity, brokerage, tax, gap, or slippage assumptions are embedded in the basic position-size calculation.')

with T[3]:
    st.subheader('Institutional cash-market flows • FII/DII')
    uploaded_flows=st.file_uploader('Upload verified FII/DII CSV if NSE blocks its endpoint',type='csv',key='flow')
    if uploaded_flows:
        try:
            flows_df=pd.read_csv(uploaded_flows); flow_err=None
            if not {'Category','Date','Net ₹Cr','Source'}.issubset(flows_df.columns):
                st.warning('CSV should include Category, Date, Net ₹Cr and Source to support auditability.')
        except Exception as exc: flows_df=pd.DataFrame(); flow_err=str(exc)
    else: flows_df,flow_err=flows()
    if not flows_df.empty:
        st.dataframe(flows_df,use_container_width=True,hide_index=True)
        st.caption('NSE figures are provisional, and the scope may include NSE-only or combined exchange flows. Verify date and scope in the source report.')
    else:
        st.warning(f"Live NSE FII/DII endpoint unavailable: {flow_err or 'No data'}. No values fabricated.")
        st.markdown('**Previously verified historical example (13 Nov 2026, NSE-only):** FII +₹5,253.98 Cr; DII −₹1,970.73 Cr. Not current-day activity.')
    st.link_button('Official NSE FII/DII report','https://www.nseindia.in/reports/fii-dii')
    st.divider()
    st.subheader('Sector strength • 5-day / 20-day relative performance')
    sector_rows=[]; sector_errors=[]
    for name,ticker in SECTORS.items():
        df,err=prices(ticker)
        if not df.empty:
            sector_rows.append({'Sector':name,'5D %':pct_return(df,5),'20D %':pct_return(df,20),'Data as of':last_dt(df),'Source':'Yahoo Finance index proxy'})
        elif err: sector_errors.append(name)
    if sector_rows:
        sec=pd.DataFrame(sector_rows).sort_values('5D %',ascending=False)
        st.dataframe(sec,use_container_width=True,hide_index=True)
        st.bar_chart(sec.set_index('Sector')['5D %'],horizontal=True)
    else: st.warning('Sector data unavailable from configured index proxies.')
    if sector_errors: st.caption('Missing sector feeds: '+', '.join(sector_errors))
    st.divider()
    st.subheader('Global developments • market proxies')
    gl=[]
    for name,ticker in GLOBAL.items():
        df,err=prices(ticker)
        if not df.empty: gl.append({'Asset':name,'Last available':safe_float(df.Close.iloc[-1]),'5D %':pct_return(df,5),'Data as of':last_dt(df)})
    if gl: st.dataframe(pd.DataFrame(gl),use_container_width=True,hide_index=True)
    else: st.warning('Global market proxy data unavailable.')
    st.divider()
    st.subheader('Moneycontrol market headlines')
    headlines,news_error=news()
    if not headlines.empty:
        for _,h in headlines.iterrows():
            st.markdown(f"- [{h['Headline']}]({h['Link']}) — {h['Published']} (Google News RSS)")
    else:
        st.warning(f'Headline feed unavailable: {news_error}. Use Moneycontrol directly.')
        st.link_button('Moneycontrol live market updates','https://www.moneycontrol.com/stocksmarketsindia/')
    st.divider()
    st.subheader('Important economic events • verified calendar')
    events=st.file_uploader('Upload economic-events CSV with source and confirmed event date',type='csv',key='events')
    if events:
        try:
            edf=pd.read_csv(events)
            required={'event','date_ist','impact','source_url','verified_at_ist'}
            if not required.issubset(edf.columns): st.error('Missing required columns: '+', '.join(sorted(required-set(edf.columns))))
            else: st.dataframe(edf,use_container_width=True,hide_index=True)
        except Exception as exc: st.error(str(exc))
    else: st.info('No verified upcoming event dates loaded. Upload a sourced calendar; dates are not guessed from headlines.')
    st.divider()
    st.subheader('Stocks to avoid / no-trade watch')
    if avoided: st.dataframe(pd.DataFrame(avoided),use_container_width=True,hide_index=True)
    else: st.info('No technical avoid flags identified from available watchlist data; this does not imply all stocks are safe.')
    st.caption('Avoid flags are model-based technical screens, not allegations or definitive fundamental judgments. Recheck news, earnings and liquidity.')

with T[4]:
    st.subheader('All shortlisted stocks • master comparison')
    if not master.empty:
        cols=['Symbol','Setup','Close ₹','Entry ₹','SL ₹','Target 1 ₹','Target 2 ₹','R:R T1','R:R T2','Beta vs NIFTY','Beta lookback','Conviction','VIX multiplier','Final units','F&O lots','Risk ₹','Status','Notes','Data as of','Price source']
        st.dataframe(master[cols],use_container_width=True,hide_index=True)
        st.download_button('↓ Download full audited master summary (CSV)',master.to_csv(index=False).encode('utf-8-sig'),file_name=f'nse_master_{now:%Y%m%d_%H%M}_IST.csv',mime='text/csv')
        st.caption('Rows reflect only successfully scanned symbols. For NIFTY 500 mode, check completion count and failed-symbol list before interpreting the ranking. Entries are conditional planning levels, not buy recommendations.')
    else: st.warning('Master summary pending live data.')

with T[5]:
    st.subheader('Sources, timestamps and verification')
    st.dataframe(pd.DataFrame([
        {'Feed':'Stock OHLCV','Provider':'Yahoo Finance / yfinance','Timestamp':'Per-symbol last available session','Status':f'{len(data)}/{len(symbols)} available'},
        {'Feed':'NIFTY benchmark','Provider':'Yahoo Finance','Timestamp':last_dt(benchmark),'Status':'OK' if not benchmark.empty else 'Missing'},
        {'Feed':'India VIX','Provider':vix_stamp,'Timestamp':vix_stamp,'Status':'OK' if vix is not None else 'Missing'},
        {'Feed':'FII/DII','Provider':'NSE official / uploaded CSV','Timestamp':'In Market intelligence table','Status':'Check separately'},
        {'Feed':'F&O contract lots','Provider':'User-uploaded exchange-sourced CSV','Timestamp':'CSV asof column','Status':f'{len(lot_map)} supplied'},
        {'Feed':'Economic calendar','Provider':'User-uploaded sourced CSV','Timestamp':'CSV verified_at_ist','Status':'Manual source required'},
        {'Feed':'Moneycontrol headlines','Provider':'Google News RSS, filtered','Timestamp':'RSS publication date','Status':'Check separately'},
    ]),hide_index=True,use_container_width=True)
    if errors:
        st.subheader('Price feed errors')
        for e in errors: st.code(e)
    if benchmark_error: st.error('NIFTY benchmark: '+benchmark_error)
    if vix_error: st.error('VIX: '+vix_error)
    st.subheader('Historical source references')
    for item in snapshot['verified_context']:
        st.markdown(f"- [{item['source']} — {item['topic']}]({item['url']}), **{item['date']}**. {item['caveat']}")
    st.warning('Yahoo Finance data can be delayed, adjusted, incomplete or blocked. Confirm against NSE/BSE and broker quotes before acting. Moneycontrol articles are contextual reporting, not an execution-grade price feed.')
    st.caption(f'Application view time: {now.isoformat()} · Python data fetch timestamp is not necessarily exchange update time.')

with T[6]:
    st.subheader('Master risk management rules')
    st.markdown(f'''1. **Risk per trade:** default configured limit {risk_pct:.1f}% of ₹{capital:,.0f} capital; total open stop-risk should be capped by a separately approved portfolio limit (illustrative policy: 3%).
2. **Portfolio concentration:** illustrative policy max 20% of capital in one equity, max 35% in one sector, and no more than two strongly correlated positions without additional review.
3. **Correlation and beta:** assess rolling daily-return correlation and 252-session beta versus NIFTY 50; beta is descriptive, not a stop-loss substitute. At least 60 paired observations are required.
4. **Slippage and gaps:** size calculations exclude gaps, fees and slippage. A stop is not a guaranteed execution price. Reject a setup if expected slippage makes the effective R:R unacceptable.
5. **Entry confirmation:** use completed daily candles for SMA6/30 crossover; require volume/price confirmation. The computed entry is a conditional planning level, not a market order.
6. **Invalidation:** bearish 6/30 cross, stop breached, material negative event, liquidity failure, or unavailable/contradictory data → re-evaluate; do not blindly average down.
7. **No-trade conditions:** missing or stale critical prices/VIX/lot sizes, unknown event risk, extreme spread, low liquidity, incorrect contract size, zero allowed lots, or unreliable market feeds.
8. **F&O:** underlying-futures approximation only. Options need a separate premium/Greeks/scenario risk model; never size options by underlying share stop alone.
9. **Fundamentals:** check P/E, PEG, ROE, growth, debt and earnings-event risk with audited company filings. Missing metrics are not interpreted as zero.
10. **Data governance:** every market fact needs a source and observation date/time; distinguish provisional FII/DII figures and news interpretation from verified prices. No automatic trading.
''')
    st.info('All limits are editable planning assumptions, not personal investment advice or exchange rules.')
    st.subheader('Fundamental due diligence for selected stock')
    if data:
        fundamental_symbol=st.selectbox('Stock',list(data.keys()),key='fundamental_symbol')
        if st.button('Fetch fundamentals for this stock'):
            info,err=fundamentals(fundamental_symbol+'.NS')
            if err: st.error('Fundamentals unavailable: '+err)
            else:
                st.dataframe(pd.DataFrame([{'Metric':k,'Value':v if v is not None else 'Missing'} for k,v in info.items()]),hide_index=True,use_container_width=True)
                st.caption('Yahoo Finance metadata is unverified third-party data; verify with latest exchange filings and Moneycontrol/Screener before decisions.')
    st.link_button('NSE historical reports','https://www.nseindia.in/static/resources/historical-reports-capital-market-daily-monthly-archives')

st.divider()
st.caption('NSE Quant Dashboard • educational decision support • no broker integration • no order placement • no synthetic market prices')
