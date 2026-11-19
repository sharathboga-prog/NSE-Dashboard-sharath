import numpy as np
import pandas as pd
from analytics import indicators, size_trade, vix_factor, trade_setup, beta_to_benchmark, conviction

def sample(n=120):
    idx = pd.bdate_range('2026-05-01', periods=n)
    close = pd.Series(np.linspace(100, 150, n), index=idx)
    return pd.DataFrame({'Open': close-0.3, 'High': close+1, 'Low':close-1, 'Close':close, 'Volume': 100000},index=idx)

def test_indicators():
    df=indicators(sample())
    assert df['SMA6'].iloc[-1] > df['SMA30'].iloc[-1]
    assert np.isfinite(df['ATR14'].iloc[-1])

def test_vix_factor():
    assert vix_factor(30,15)==0.5
    assert vix_factor(10,15)==1
    assert vix_factor(None) is None

def test_lot_rounding():
    x=size_trade(100000,1,100,95,20,lot_size=75)
    assert x['base_units']==200
    assert x['vix_factor']==0.75
    assert x['contracts']==2
    assert x['final_units']==150
    assert x['rupee_risk']==750

def test_missing_vix():
    assert size_trade(100000,1,100,95,None)['status'].startswith('Pending')

def test_invalid_sl():
    assert size_trade(100000,1,100,101,15)['status'].startswith('Invalid')

def test_setup():
    d=indicators(sample())
    x=trade_setup(d)
    assert x['entry'] > x['stop']
    assert x['target1'] > x['entry']

def test_beta():
    a=sample()['Close']; b=a*2
    beta,n=beta_to_benchmark(a,b)
    assert n>=60 and abs(beta-1)<.001

def test_conviction():
    level,*_=conviction(indicators(sample()))
    assert level in ['Low','Medium','High','Very High']
