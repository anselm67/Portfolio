#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import numpy as np
import math

parser = argparse.ArgumentParser(description="Explores a rebalncing strategy.")
parser.add_argument('--symbol', type=str, default='VTI',
                    help='Initial amount of cash to work with.')
parser.add_argument('--cash', type=int, default=10000,
                    help='Stock symbol to work with.')
parser.add_argument('--target', type=float, default=0.2,
                    help='Target allocation ratio of cash.')
parser.add_argument('--bound', type=float, default=0.25,
                    help='Bounds for buy/sell trigger; Sell at (1-bound)*target and buy at (1+bound)*target.')
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help='Chat some as we procceed.')
# Executable commands from command line. None passed? We'll just run rebalance.
parser.add_argument('--plot-by-target', action='store_true', default=False,
                    help='Plot gains by varying target cash allocation ratios from 0 to 1.')
parser.add_argument('--plot-by-bound', action='store_true', default=False,
                    help='Plot gains by varying trigger bound from 0.1 to 0.5')
args = parser.parse_args()

def verbose(level: int, msg: str):
    if args.verbose >= level:
        print(msg)

def rebalance(data: pd.DataFrame, 
            target: float, 
            initial_cash: float, 
            bound: float=.25):
    price = data.iloc[0].Close
    stock = math.floor((1.0 - target) * initial_cash / price)
    cash = initial_cash - stock * price

    def display(level=1, prefix=''):
        verbose(level, f"{prefix}${cash + stock * price:<9,.2f}: {stock} shares @ ${price:.2f} and ${cash:.2f} {100.0 * cash / (cash + stock * price):.2f}%")
    display()
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
    display()
    return cash + stock * price

def plot_by_target(data):
    scope = np.linspace(0, 1.0, 50)
    plt.plot(scope, np.array([rebalance(data, target, args.cash) for target in scope]))
    plt.show()

def plot_by_bound(data):
    scope = np.linspace(0.1, 0.5, 20)
    plt.plot(scope, np.array([rebalance(data, args.target, args.cash, bound) for bound in scope]))
    plt.show()

def main():
    verbose(1, f"Fetching {args.symbol} data...")
    ticker = yf.Ticker(args.symbol)
    data = ticker.history(period='max', end=pd.Timestamp.today(), interval='1d')
    verbose(1, f"Using {args.symbol} data from {data.index[0]} till {data.index[-1]}")
    if args.plot_by_target:
        plot_by_target(data)
    elif args.plot_by_bound:
        plot_by_bound(data)
    else:
        value = rebalance(data, args.target, args.cash, args.bound)
        gains = value - args.cash
        print(f"${args.cash:,.2f} => ${value:,.2f} {'Up' if gains > 0 else 'Down'} ${gains:,.2f} or {100.0 * (value - args.cash) / args.cash:.2f}%")

if __name__ == "__main__":
    main()


