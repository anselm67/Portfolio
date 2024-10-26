#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from typing import Tuple

import argparse
import pandas as pd
import yfinance as yf # type: ignore
import math
import sys
import datetime

def parse_range(arg: str, 
                min_value: float = 0.0, max_value: float = 1.0, 
                ordered: bool = True) -> Tuple[float, float]:
    try:
        lower, upper = (0, 0)
        values = arg.split(':')
        if len(values) == 1:
            lower, upper = float(arg), float(arg)
        else:
            lower, upper = float(values[0]), float(values[1])
        if not ( min_value <= lower <= max_value):
            raise ValueError(f"Lower bound {lower} should be in [{min_value}:{max_value}]")
        if not ( min_value <= upper <= max_value):
            raise ValueError(f"Upper bound {lower} should greater than [{min_value}:{max_value}]")
        if ordered and lower > upper:
            raise ValueError(f"Lower bound should be greater than upper boud {upper}")
        return (lower, upper)
    except ValueError as ex:
        print(ex)
        raise argparse.ArgumentTypeError(f"Invalid range {arg}, expect 'lower:upper'")

parser = argparse.ArgumentParser(
    prog='rebalance.py',
    description="Explores a rebalancing strategy."
)
parser.add_argument('--symbol', type=str, default='VTI',
                    help='Stock symbol to work with.')
parser.add_argument('--cash', type=int, default=10000,
                    help='Initial amount of cash to work with.')
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help='Chat some as we procceed.')
parser.add_argument('--count', type=int, default=12,
                    help='Number of purchases to make.')
parser.add_argument('--target', type=int, default=0.2,
                    help='Target cash allocation by end of purchase period.')
parser.add_argument('--freq', default='W-MON',
                    help='Frequency of purchases, e.g. "ME", "W-MON" ...')
parser.add_argument('--from', type=datetime.date.fromisoformat, default=None,
                    dest='from_datetime',
                    help='Restrict analysis to data later than this date (YYYY-MM-DD)')
parser.add_argument('--till', type=datetime.date.fromisoformat, default=None,
                    dest='till_datetime',
                    help='Restrict analysis to data earlier than this date (YYYY-MM-DD)')

args = parser.parse_args()

def verbose(level: int, msg: str):
    if args.verbose >= level:
        print(msg)

def exit(msg: str):
    sys.exit(msg)

def annual_returns(data: pd.DataFrame, start_value: float, end_value: float):
    days = (data.index[-1] - data.index[0]).days
    gain = 1.0 + (end_value - start_value) / start_value
    per_day = math.pow(gain, 1 / days)
    return 100.0 * (math.pow(per_day, 365) - 1.0) if abs(per_day) > 0 else 0

# Enters the market with initial_cash.
def enter(data: pd.DataFrame, 
          initial_cash: float, target: float,
          freq: str = args.freq, count: int = args.count) -> pd.DataFrame:
    """Enters the market through count purchases of stock at given frequency.

    Purchases (1 - target_ * inital_cash) / count of stock, count times at the given frequency.
    
    Args:
        data (pd.DataFrame): Stock ticker as obtained from yfinance.
        initial_cash (float): Initial cash position.
        target (float): Target cash allocation to put aside before entering the market, this will be left unchanged in the cash position.
        freq (str, optional): Frequency of purchases . Defaults to args.freq.
        count (int, optional): Amount of times to make purchase. Defaults to args.count.

    Returns:
        pd.DataFrame: The input DataFrame augmented with Cash, Position and Value columns.
    """
    # Enter the market over a year, buy every week
    cash_reserve = target * initial_cash
    initial_cash -= cash_reserve
    amount_step = initial_cash / count
    out = data.copy()
    out['Purchase'] = False
    out.loc[out.asfreq(freq).dropna().index, 'Purchase'] = True
    
    # Setup initial values
    price: float = out.iloc[0].Close
    position = math.floor(amount_step / price) 
    cash = initial_cash - position * price
    count -= 1
    class State:
        def __init__(self):
            self.position = [ position ]
            self.cash = [ cash + cash_reserve ]
            self.value = [ position * price + cash ]
            self.index = [ data.index[0] ]
    state = State()
    for ts, row in out[1:].iterrows():
        if row.Purchase and count > 0:
            buy = math.floor(min(amount_step, cash) / row.Close)
            if buy > 0:
                position += buy
                cash -= buy * row.Close
                verbose(level=1, msg=f"[{count}] {ts} BUY {buy} => "
                        f"${cash + cash_reserve:,.2f} "
                        f"{position}/${position * row.Close:,.2f} "
                        f"${cash + cash_reserve + position * row.Close:,.2f}")
            count -= 1
        state.position.append(position)
        state.cash.append(cash + cash_reserve)
        state.value.append(cash + position * row.Close)
        state.index.append(ts)
    return data.copy().join([
        pd.Series(state.position, name='Position', index=state.index), 
        pd.Series(state.cash, name='Cash', index=state.index), 
        pd.Series(state.value, name='Value', index=state.index)
    ])

def enter2(data: pd.DataFrame, 
           initial_cash: float,
           target: float,
           freq: str = args.freq, count: int = args.count):
    # Enter the market over a year, buy every week
    final_target = (1 - 0.2)
    target_step = final_target / count
    out = data.copy()
    out['Rebalance'] = False
    out.loc[out.asfreq(freq).dropna().index, 'Rebalance'] = True
    
    # Setup initial values
    price = out.iloc[0].Close
    target = final_target / count
    position = math.floor(target * initial_cash / price)
    cash = initial_cash - position * price
    count -= 1
    class State:
        def __init__(self):
            self.position = [ position ]
            self.cash = [ cash ]
            self.value = [ position * price + cash ]
            self.index = [ data.index[0] ]
    state = State()

    for ts, row in out[1:].iterrows():
        if row.Rebalance and count > 0:
            value = cash + position * row.Close
            target += target_step
            buy = math.floor((target * value) / row.Close) - position
            if buy > 0:
                cash -= row.Close * buy
                position += buy
                verbose(level=1, msg=f"[{count}] {ts} BUY {buy} => ${cash:,.2f} {position}/${position * row.Close:,.2f} ${cash + position * row.Close:,.2f}")
            count -= 1
        state.position.append(position)
        state.cash.append(cash)
        state.value.append(position * row.Close + cash)
        state.index.append(ts)
    return data.copy().join([
        pd.Series(state.position, name='Position', index=state.index), 
        pd.Series(state.cash, name='Cash', index=state.index), 
        pd.Series(state.value, name='Value', index=state.index)
    ])

def display(out: pd.DataFrame):
    row = out.iloc[-1]
    print(f"{out.index[-1]} => "
        f"Cash ${row.Cash:,.2f} "
        f"Position {row.Position:,.2f} "
        f"Value: ${row.Value:,.2f} "
        f"YoY {annual_returns(out, args.cash, row.Value):.2f}%")

def main():
    # Fetch and cut the data according to the command line.
    ticker = yf.Ticker(args.symbol)
    data = ticker.history(period='max', end=pd.Timestamp.today(), interval='1d')
    data = data.tz_localize(None)
    if args.from_datetime is not None:
        data = data[args.from_datetime:]
    if args.till_datetime is not None:
        data = data[:args.till_datetime]
    if len(data) == 0:
        exit(f"No data available for {args.symbol}, check your spelling.")
    # Do as requested.
    verbose(1, f"Using {args.symbol} data from {data.index[0]} till {data.index[-1]}")
    out = enter(data, args.cash, args.target)    
    display(out)
    out = enter2(data, args.cash, args.target)
    display(out)

if __name__ == "__main__":
    main()


