"""Deterministic trading analytics. No network calls or order placement."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def safe_float(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Use split-adjusted OHLC where available; no lookahead."""
    df = frame.copy().sort_index()
    for key in ("Open", "High", "Low", "Close", "Volume"):
        if key not in df:
            raise ValueError(f"Missing OHLCV column: {key}")
        df[key] = pd.to_numeric(df[key], errors="coerce")
    df["SMA6"] = df["Close"].rolling(6, min_periods=6).mean()
    df["SMA30"] = df["Close"].rolling(30, min_periods=30).mean()
    prev_close = df["Close"].shift(1)
    tr = pd.concat([(df["High"] - df["Low"]), (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()], axis=1).max(axis=1)
    df["ATR14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    change = df["Close"].diff()
    gain = change.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    df.loc[(loss == 0) & (gain > 0), "RSI14"] = 100
    df.loc[(loss == 0) & (gain == 0), "RSI14"] = 50
    df["Vol20"] = df["Volume"].rolling(20, min_periods=20).mean()
    df["VolRatio"] = df["Volume"] / df["Vol20"].replace(0, np.nan)
    df["Resistance20"] = df["High"].shift(1).rolling(20, min_periods=20).max()
    df["Support10"] = df["Low"].shift(1).rolling(10, min_periods=10).min()
    df["BullCross"] = (df["SMA6"] > df["SMA30"]) & (df["SMA6"].shift(1) <= df["SMA30"].shift(1))
    df["BearCross"] = (df["SMA6"] < df["SMA30"]) & (df["SMA6"].shift(1) >= df["SMA30"].shift(1))
    return df


def beta_to_benchmark(close: pd.Series, benchmark_close: pd.Series, lookback: int = 252):
    pair = pd.concat([close.pct_change(), benchmark_close.pct_change()], axis=1).dropna().tail(lookback)
    if len(pair) < 60:
        return None, len(pair)
    variance = pair.iloc[:, 1].var(ddof=1)
    if not variance or not math.isfinite(variance):
        return None, len(pair)
    return safe_float(pair.iloc[:, 0].cov(pair.iloc[:, 1]) / variance), len(pair)


def vix_factor(vix, baseline=15.0, floor=0.50):
    """User-configurable heuristic, NOT a validated prediction or exchange rule."""
    vix, baseline, floor = map(safe_float, (vix, baseline, floor))
    if vix is None or vix <= 0 or baseline is None or baseline <= 0 or floor is None or not 0 < floor <= 1:
        return None
    return round(max(floor, min(1.0, baseline / vix)), 4)


def size_trade(capital, risk_pct, entry, stop, vix, baseline=15.0, floor=0.50, lot_size=None):
    """Long-equity/futures-underlying approximation; option premiums require separate model.

    Base units = floor((capital*risk_pct/100)/abs(entry-stop));
    adjusted units = floor(base units * factor). For futures, round DOWN to
    complete exchange-defined lots; NEVER change exchange lot size.
    """
    cap, pct, ent, sl = map(safe_float, (capital, risk_pct, entry, stop))
    factor = vix_factor(vix, baseline, floor)
    if any(x is None for x in (cap, pct, ent, sl)) or cap <= 0 or not 0 < pct <= 100 or ent <= 0 or sl < 0 or sl >= ent:
        return {"status": "Invalid capital, risk, entry or stop"}
    if factor is None:
        return {"status": "Pending India VIX and adjustment inputs"}
    unit_risk = ent - sl
    budget = cap * pct / 100
    base_units = math.floor(budget / unit_risk)
    adjusted_units = math.floor(base_units * factor)
    lots = None
    if lot_size is not None:
        lot = safe_float(lot_size)
        if lot is None or lot <= 0 or not lot.is_integer():
            return {"status": "Invalid exchange lot size"}
        lot = int(lot)
        lots = adjusted_units // lot
        adjusted_units = lots * lot
    return {"status": "OK" if adjusted_units > 0 else "No trade: size below minimum", "risk_budget": budget,
            "unit_risk": unit_risk, "base_units": base_units, "vix_factor": factor,
            "final_units": adjusted_units, "contracts": lots, "rupee_risk": round(adjusted_units * unit_risk, 2),
            "notional": round(adjusted_units * ent, 2)}


def trade_setup(df: pd.DataFrame):
    """Planning levels, not investment recommendations. Require sufficient OHLCV."""
    if len(df) < 35:
        return {"status": "Insufficient history"}
    last = df.iloc[-1]
    price, resistance, support, atr = [safe_float(last.get(k)) for k in ("Close", "Resistance20", "Support10", "ATR14")]
    if any(v is None for v in (price, resistance, support, atr)) or atr <= 0:
        return {"status": "Incomplete indicator data"}
    entry = round(max(price, resistance) * 1.002, 2)
    stop = round(min(support, entry - 1.5 * atr), 2)
    if stop <= 0 or stop >= entry:
        return {"status": "Invalid computed stop"}
    risk = entry - stop
    target1, target2 = round(entry + 1.5 * risk, 2), round(entry + 2.5 * risk, 2)
    return {"status": "Planning only", "entry": entry, "stop": stop,
            "target1": target1, "target2": target2, "rr1": round((target1-entry)/risk, 2),
            "rr2": round((target2-entry)/risk, 2), "support": round(support, 2), "resistance": round(resistance, 2)}


def conviction(df: pd.DataFrame, benchmark_up=None, sector_up=None):
    """Transparent rule score; NOT a calibrated probability."""
    if len(df) < 35:
        return "Pending", 0, [], ["Insufficient history"]
    row = df.iloc[-1]
    required = ["Close", "SMA6", "SMA30", "RSI14", "VolRatio", "Resistance20"]
    if any(safe_float(row.get(k)) is None for k in required):
        return "Pending", 0, [], ["Missing indicators"]
    recent = df["BullCross"].tail(5).fillna(False).any()
    rules = {
        "SMA6 above SMA30": row["SMA6"] > row["SMA30"],
        "Bullish crossover in last 5 sessions": recent,
        "Close above SMA30": row["Close"] > row["SMA30"],
        "RSI 50–70": 50 <= row["RSI14"] <= 70,
        "Volume >= 1.5x 20-day average": row["VolRatio"] >= 1.5,
        "Close above prior 20-day resistance": row["Close"] > row["Resistance20"],
    }
    if benchmark_up is not None:
        rules["Benchmark 20-day trend positive"] = bool(benchmark_up)
    if sector_up is not None:
        rules["Sector 20-day trend positive"] = bool(sector_up)
    positives = [k for k,v in rules.items() if v]
    negatives = [k for k,v in rules.items() if not v]
    score = len(positives) / len(rules)
    level = "Very High" if score >= .85 else "High" if score >= .65 else "Medium" if score >= .40 else "Low"
    return level, len(positives), positives, negatives
