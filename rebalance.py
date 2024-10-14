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
parser.add_argument('--target', type=float, default=0.2,
                    help='Target allocation ratio of cash.')
parser.add_argument('--bound', type=lambda s : parse_range(s, ordered=False), default=(0.25, 0.25),
                    metavar='lower:upper',
                    help="""Bounds for buy/sell trigger; Sell at (1-lower)*target and buy at (1+upper)*target.
                    If provided as BOUND the range is [BOUND, -BOUND], otherwise it can be proivided as LOWER:UPPER""")
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
parser.add_argument('--plot-by-target', nargs='?', const='0.0:1.0',
                    metavar='from:to',
                    type=parse_range,
                    help="""Plot gains by varying target cash allocation ratios from 0 to 1.
You can changes the bounds by providing them e.g. --plot-by-target from:to""")
parser.add_argument('--plot-by-bound', nargs='?', const='0.1:0.5',
                    metavar='from:to',
                    type=parse_range,
                    help="""Plot gains by varying trigger bound defaults to 0.1 to 0.5.
You can change the bounds by providing them e.g. --plot from:to""")

args = parser.parse_args()

def verbose(level: int, msg: str):
    if args.verbose >= level:
        print(msg)

def exit(msg: str):
    sys.exit(msg)

def rebalance_values(data: pd.DataFrame, 
                     target: float, 
                     initial_cash: float, 
                     bound: tuple[float, float]=(0.25, .25)):
    price = data.iloc[0].Close
    stock = math.floor((1.0 - target) * initial_cash / price)
    cash = initial_cash - stock * price
    value = [(data.index[0], 0, initial_cash)]
    def display(level=1, prefix=''):
        verbose(level, f"{prefix}${cash + stock * price:<9,.2f}: {stock} shares @ ${price:.2f} and ${cash:.2f} {100.0 * cash / (cash + stock * price):.2f}%")
    display(prefix="Start => ")
    for ts, row in data.shift(-1).iterrows():
        if np.isnan(row.Close):
            break
        price = row.Close
        new_total = cash + stock * price
        if cash / new_total < (1.0 - bound[0]) * target:
            target_cash = target* new_total
            sell = math.floor((target_cash - cash) / price)
            if sell > 0:
                stock -= sell
                cash += sell * price
                display(2, f"{ts} SOLD   {sell:3d} => ")
        elif cash / new_total > (1.0 + bound[1]) * target:
            target_cash = target * new_total
            buy = math.floor((cash - target_cash) / price)
            if buy > 0:
                stock += buy
                cash -= buy * price
                display(2, f"{ts} BOUGHT {buy:3d} => ")
        value.append((ts, stock, cash + stock * price))
    display(prefix="Finish => ")
    return pd.DataFrame(
        { 'Position': [v[1] for v in value], 'Total': [v[2] for v in value] },
        index = [v[0] for v in value],
    )

def rebalance(data: pd.DataFrame, 
            target: float, 
            initial_cash: float, 
            bound: tuple[float, float]=(0.25, 0.25)):
    values = rebalance_values(data, target, initial_cash, bound)
    return values.iloc[-1].Total

def plot_by_target(data):
    scope = np.linspace(0, 1.0, 50)
    plt.plot(scope, np.array([rebalance(data, target, args.cash) for target in scope]))
    plt.show()

def plot_by_bound(data: pd.DataFrame, from_bound: float, to_bound: float):
    scope = np.linspace(from_bound, to_bound, 25)
    plt.plot(scope, np.array([rebalance(data, args.target, args.cash, (bound, bound)) for bound in scope]))
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
        plot_by_bound(data, args.plot_by_bound[0], args.plot_by_bound[1])
    else:
        if args.plot:
            out = rebalance_values(data, args.target, args.cash, args.bound)
            value = out.iloc[-1].Total
            fig, ax1 = plt.subplots()
            ax1.set_xlabel('time')
            ax1.set_ylabel('Position', color='tab:red')
            ax1.plot(out.index, out.Position, color='tab:red')
            ax2 = ax1.twinx()
            ax2.set_ylabel('Total Value', color='tab:blue')
            ax2.plot(out.index, out.Total, color='tab:blue')
            fig.tight_layout()
            plt.show()
        else:
            value = rebalance(data, args.target, args.cash, args.bound)
        gains = value - args.cash
        print(f"${args.cash:,.2f} => ${value:,.2f} {'Up' if gains > 0 else 'Down'} ${gains:,.2f} or {100.0 * (value - args.cash) / args.cash:.2f}%")

if __name__ == "__main__":
    main()


