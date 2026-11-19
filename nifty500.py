"""Official NSE Indices constituent loader. Never silently substitute an unofficial list."""
from io import StringIO
import pandas as pd
import requests

OFFICIAL_URL = 'https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv'
ALTERNATE_URL = 'https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv'

def fetch_constituents(timeout=15):
    headers={'User-Agent':'Mozilla/5.0 (compatible; NSEQuantResearch/1.0)', 'Accept':'text/csv,*/*'}
    errors=[]
    for url in (OFFICIAL_URL,ALTERNATE_URL):
        try:
            r=requests.get(url,headers=headers,timeout=timeout)
            r.raise_for_status()
            df=pd.read_csv(StringIO(r.text))
            cols={str(c).strip().lower():c for c in df.columns}
            if 'symbol' not in cols: raise ValueError('No Symbol column in NSE constituent CSV')
            symbols=df[cols['symbol']].dropna().astype(str).str.strip().str.upper().tolist()
            symbols=list(dict.fromkeys(x for x in symbols if x and x!='NAN'))
            if not 450<=len(symbols)<=510: raise ValueError(f'Unexpected constituent count: {len(symbols)}')
            return symbols,url
        except Exception as exc: errors.append(f'{url}: {exc}')
    raise RuntimeError('Official NIFTY 500 list unavailable; '+ '; '.join(errors))
