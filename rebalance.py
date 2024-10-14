#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import numpy as np
import math
import sys
import datetime

parser = argparse.ArgumentParser(
    prog='rebalance.py',
    description="Explores a rebalancing strategy."
)
parser.add_argument('--symbol', type=str, default='VTI',
                    help='Stock symbol to work with.')
parser.add_argument('--cash', type=int, default=10000,
                    help='Initial amount of cash to work with.')
parser.add_argument('--target', type=float, default=0.2,
                    help='Target allocation ratio of cash.')
parser.add_argument('--bound', type=float, default=0.25,
                    help='Bounds for buy/sell trigger; Sell at (1-bound)*target and buy at (1+bound)*target.')
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help='Chat some as we procceed.')
parser.add_argument('--from', type=datetime.date.fromisoformat, default=None,
                    dest='from_datetime',
                    help='Restrict analysis to data later than this date (YYYY-MM-DD)')
parser.add_argument('--till', type=datetime.date.fromisoformat, default=None,
                    dest='till_datetime',
                    help='Restrict analysis to data earlier than this date (YYYY-MM-DD)')
# Executable commands from command line. None passed? We'll just run rebalance.
parser.add_argument('--plot', action='store_true', default=False,
                    help='Plot portfolio values by dates.')
parser.add_argument('--plot-by-target', action='store_true', default=False,
                    help='Plot gains by varying target cash allocation ratios from 0 to 1.')
parser.add_argument('--plot-by-bound', action='store_true', default=False,
                    help='Plot gains by varying trigger bound from 0.1 to 0.5')

args = parser.parse_args()

def verbose(level: int, msg: str):
    if args.verbose >= level:
        print(msg)

def exit(msg: str):
    sys.exit(msg)

def rebalance_values(data: pd.DataFrame, 
                     target: float, 
                     initial_cash: float, 
                     bound: float=.25):
    price = data.iloc[0].Close
    stock = math.floor((1.0 - target) * initial_cash / price)
    cash = initial_cash - stock * price
    value = [(data.index[0], initial_cash)]
    def display(level=1, prefix=''):
        verbose(level, f"{prefix}${cash + stock * price:<9,.2f}: {stock} shares @ ${price:.2f} and ${cash:.2f} {100.0 * cash / (cash + stock * price):.2f}%")
    display(prefix="Start => ")
    for ts, row in data.shift(-1).iterrows():
        if np.isnan(row.Close):
            break
        price = row.Close
        new_total = cash + stock * price
        if cash / new_total < (1.0 - bound) * target:
            target_cash = target* new_total
            sell = math.floor((target_cash - cash) / price)
            if sell > 0:
                stock -= sell
                cash += sell * price
                display(2, f"{ts} SOLD   {sell:3d} => ")
        elif cash / new_total > (1.0 + bound) * target:
            target_cash = target * new_total
            buy = math.floor((cash - target_cash) / price)
            if buy > 0:
                stock += buy
                cash -= buy * price
                display(2, f"{ts} BOUGHT {buy:3d} => ")
        value.append((ts, cash + stock * price))
    display(prefix="Finish => ")
    return pd.Series(name = 'Total', 
                     data = [v[1] for v in value],
                     index = [v[0] for v in value])

def rebalance(data: pd.DataFrame, 
            target: float, 
            initial_cash: float, 
            bound: float=.25):
    values = rebalance_values(data, target, initial_cash, bound)
    return values.iloc[-1]

def plot_by_target(data):
    scope = np.linspace(0, 1.0, 50)
    plt.plot(scope, np.array([rebalance(data, target, args.cash) for target in scope]))
    plt.show()

def plot_by_bound(data):
    scope = np.linspace(0.1, 0.5, 50)
    plt.plot(scope, np.array([rebalance(data, args.target, args.cash, bound) for bound in scope]))
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
    if args.plot_by_target:
        plot_by_target(data)
    elif args.plot_by_bound:
        plot_by_bound(data)
    else:
        if args.plot:
            series = rebalance_values(data, args.target, args.cash, args.bound)
            value = series.iloc[-1]
            plt.plot(series.index, series.values)
            plt.show()
        else:
            value = rebalance(data, args.target, args.cash, args.bound)
        gains = value - args.cash
        print(f"${args.cash:,.2f} => ${value:,.2f} {'Up' if gains > 0 else 'Down'} ${gains:,.2f} or {100.0 * (value - args.cash) / args.cash:.2f}%")

if __name__ == "__main__":
    main()


