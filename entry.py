#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import numpy as np
import math
import sys
import datetime

def parse_range(arg: str, min_value = 0.0, max_value = 1.0, ordered=True):
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
parser.add_argument('--count', type=int, default=30,
                    help='Number of purchases to make.')
parser.add_argument('--every', default=10,
                    help='Frequency - in business days - of purchases.')
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

def yearly_returns(data: pd.DataFrame, start_value: float, end_value: float):
    days = (data.index[-1] - data.index[0]).days
    gain = 1.0 + (end_value - start_value) / start_value
    per_day = math.pow(gain, 1 / days)
    return 100.0 * (math.pow(per_day, 365) - 1.0) if abs(per_day) > 0 else 0

# Enters the market with initial_cash.
def enter(data: pd.DataFrame, 
          initial_cash: float, 
          count: int = args.count,
          every: int = args.every):
    amount = initial_cash / count
    cash = initial_cash
    stock = 0
    for ts, row in data.iloc[::every].iterrows():
        quantity = math.floor(min(amount, cash) / row.Close)
        if quantity > 0:
            verbose(2, f"{ts} => BUY {quantity} @ {row.Close:.2f}")
            stock += quantity
            cash -= quantity * row.Close
        count -= 1
        if count <= 0:
            break
    # (value, position, cash)
    return stock * data.iloc[-1].Close, stock, cash

def enter2(data: pd.DataFrame, 
            initial_cash: float,
            freq = 'ME', count = 12):
    # Enter the market over a year, buy every week
    final_target = (1 - 0.01)
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

def plot_by_every(data: pd.DataFrame):
    scope = range(1, 10)
    def value(every: int):
        value, _, _ = enter(data, args.cash, count=25, every=every)
        yoy = yearly_returns(data, args.cash, value)
        verbose(1, f"Freq {every} over {25*every} days => ${value:,.2f} YoY {yoy:.2f}")
        return yoy
    plt.plot(scope, [value(every) for every in scope])
    plt.show()

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
    (value, position, cash) = enter(data, args.cash, count = 12, every = 30)
    print(f"Bought {position} shares. ${cash:.2f} left => ${value:,.2f}")
#    plot_by_every(data)
    out = enter2(data, args.cash)
    print(out.tail(1))

if __name__ == "__main__":
    main()


