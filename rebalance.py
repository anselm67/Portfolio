#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from typing import Tuple

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf # type: ignore
import numpy as np
import math
import sys
import datetime

def parse_range(arg: str, 
                min_value: float = 0.0, max_value: float = 1.0, 
                ordered: bool=True) -> Tuple[float, float]:
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

def annual_returns(data: pd.DataFrame, start_value: float, end_value: float) -> float:
    days = (data.index[-1] - data.index[0]).days
    gain = 1.0 + (end_value - start_value) / start_value
    per_day = math.pow(gain, 1 / days)
    return 100.0 * (math.pow(per_day, 365) - 1.0) if abs(per_day) > 0 else 0

def rebalance(data: pd.DataFrame, 
              target: float, 
              initial_cash: float, 
              bound: tuple[float, float]=(0.25, .25)) -> pd.DataFrame:
    """Rebalances a portfolio to achieve the given cash target allocation.

    Args:
        data (pd.DataFrame): The ticker's history as obtained from yfinance
        target (float): Target cash allocatioon between 0.0 and 1.0
        initial_cash (float): Initial cash position
        bound (tuple[float, float], optional): Sell and (resp.) buy bounds. 
            Sell is trigerred when the cash position is below (target - sell) * cash. 
            Resp. purchase is triggered when the cash position is above (target + buy) * cash
            Defaults to (0.25, .25).

    Returns:
        pd.DataFrame: The inputp frame with Cash, Value and Position columns added.
    """
    price = data.iloc[0].Close
    stock = math.floor((1.0 - target) * initial_cash / price)
    cash = initial_cash - stock * price
    class State:
        def __init__(self):
            self.position = [ stock ]
            self.cash = [ cash ]
            self.value = [ stock * price + cash ]
            self.index = [ data.index[0] ]
    state = State()
    def display(level: int=1, prefix: str=''):
        verbose(level, f"{prefix}${cash + stock * price:<9,.2f}: {stock} shares @ ${price:.2f} and ${cash:.2f} {100.0 * cash / (cash + stock * price):.2f}%")
    display(prefix=f"{data.index[0].strftime('%Y-%m-%d')} => ")
    for ts, row in data[1:].iterrows():
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
        state.position.append(stock)
        state.cash.append(cash)
        state.value.append(cash + stock * price)
        state.index.append(ts)
    display(prefix=f"\t{data.index[-1].strftime('%Y-%m-%d')} => ")
    return data.copy().join([
        pd.Series(state.position, name='Position', index=state.index), 
        pd.Series(state.cash, name='Cash', index=state.index), 
        pd.Series(state.value, name='Value', index=state.index)
    ])

def plot_by_target(data: pd.DataFrame):
    def value(target: float):
        out = rebalance(data, target, args.cash)
        return annual_returns(data, args.cash, out.iloc[-1].Value)
    scope = np.linspace(0, 1.0, 50)
    plt.plot(scope, np.array([value(target) for target in scope]))
    plt.show()

def plot_by_bound(data: pd.DataFrame, from_bound: float, to_bound: float):
    def value(bound: float):
        out = rebalance(data, args.target, args.cash, (bound, bound))
        return annual_returns(data, args.cash, out.iloc[-1].Value)
    scope = np.linspace(from_bound, to_bound, 25)
    plt.plot(scope, np.array([value(bound) for bound in scope]))
    plt.show()

def plot_portfolio(out: pd.DataFrame):
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('time')
    ax1.set_ylabel('Position', color='tab:red')
    ax1.plot(out.index, out.Position, color='tab:red')
    ax2 = ax1.twinx()
    ax2.set_ylabel('Total Value', color='tab:blue')
    ax2.plot(out.index, out.Value, color='tab:blue')
    ax2.plot(out.index, out.Cash, color='tab:green')
    fig.tight_layout()
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
        out = rebalance(data, args.target, args.cash, args.bound)
        value = out.iloc[-1].Value
        gains = value - args.cash
        print(f"${args.cash:,.2f} => ${value:,.2f} " \
                f"{'Up' if gains > 0 else 'Down'} ${gains:,.2f} " \
                f"or {100.0 * (value - args.cash) / args.cash:.2f}% " \
                f"yearly {annual_returns(data, args.cash, value):.2f}%")
        if args.plot:
            plot_portfolio(out)

if __name__ == "__main__":
    main()


