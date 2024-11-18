import math
from datetime import date

import pandas as pd


def percent(part: float, total: float, default_str: str = "--") -> str :
    if total > 0: 
        return f"{100.0 * part / total:,.2f}" 
    else: 
        return default_str

def dollars(value: float) -> str:
    if value >= 1000000:
        return f"${value / 1000000.:,.2f}m"
    elif value > 1000:
        return f"${value / 1000.:,.0f}k"
    else:
        return f"${value:,.2f}"
    
def as_timestamp(x: str | pd.Timestamp) -> pd.Timestamp:
    if isinstance(x, str):
        return pd.Timestamp(x, tz='UTC')
    else:
        assert isinstance(x, pd.Timestamp), f"{x} should be a string or Timestamp"
        return x

def as_date(date_or_timestamp: date | pd.Timestamp) -> date:
    if isinstance(date_or_timestamp, pd.Timestamp):
        return date_or_timestamp.date()
    else:
        return date_or_timestamp
    
def annual_returns(index: pd.DatetimeIndex, start_value: float, end_value: float) -> float:
    days = float((index[-1] - index[0]).days) 
    gain = 1.0 + (end_value - start_value) / start_value
    per_day = math.pow(gain, 1. / days) if days > 0 else 1
    return 100.0 * (math.pow(per_day, 365) - 1.0) if abs(per_day) > 0 else 0

