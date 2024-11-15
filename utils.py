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

