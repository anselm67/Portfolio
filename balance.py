#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

import argparse
import datetime
import math
import sys
from typing import List, Set, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from portfolio import Portfolio
from utils import dollars
from yfcache import YFCache


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
    prog='balance.py',
    description="Explores a rebalancing strategy."
)
parser.add_argument('portfolios', nargs='*',
                    help='Json portfolio file.')
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
parser.add_argument('--plot', action='store_true', default=False,
                    help='Plot portfolio values by dates.')
# Cache related commands
parser.add_argument('--clear-cache', action='store_true', default=False,
                    help='Clears the ticker cache.')
parser.add_argument('--update-cache', action='store_true', default=False,
                    help='Updates the cache with the freshest stock quotes.')

args = parser.parse_args()

def verbose(level: int, msg: str):
    if args.verbose >= level:
        print(msg)

def exit(msg: str):
    sys.exit(msg)

def annual_returns(data: pd.DataFrame, start_value: float, end_value: float) -> float:
    days = float((data.index[-1] - data.index[0]).days) # type: ignore
    gain = 1.0 + (end_value - start_value) / start_value
    per_day = math.pow(gain, 1. / days) if days > 0 else 1
    return 100.0 * (math.pow(per_day, 365) - 1.0) if abs(per_day) > 0 else 0

ALLOC = {
    'GOOG': 0.1,
    'VTI': 0.4,
    'QQQ': 0.2,
}

def plot_values(pd: pd.DataFrame, names: List[ str ], values: List[ List[ float ] ]):
    def formatter(value: float, _: float) -> str:
        return dollars(value)
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('time')
    ax1.set_ylabel('Position', color='tab:blue')
    for n, v in zip(names, values):
        ax1.plot(pd.index, v, label=n)         # type: ignore
    fig.tight_layout()
    ax1.yaxis.set_major_formatter(FuncFormatter(formatter))
    plt.legend(title='Portfolios')
    plt.show()

def do_portfolios(yfcache: YFCache):
    if len(args.portfolios) == 0:
        return
    portfolios = [Portfolio.load(f) for f in args.portfolios]
    tickers: Set[ str ] = set()
    for p in portfolios:
        tickers.update(p.tickers())
    prices = yfcache.join(list(tickers), 
                          from_datetime=args.from_datetime,
                          till_datetime=args.till_datetime).dropna()
    if len(prices) == 0:
        raise AssertionError("Empty price list, check your tickers.")
    values: List[ List[float] ] = [ [].copy() for _ in portfolios ]
    for _, row in prices.iterrows():
#        for op in p.balance({
#            symbol: row[symbol] for symbol in tickers
#        }, args.bound, timestamp):  # type: ignore
#            print(op)
        for p, v in zip(portfolios, values):
            v.append(p.value({
                symbol: row[symbol] for symbol in tickers
            }))
    for p, v in zip(portfolios, values):
        print(p)
        print(f"Annual returns: {annual_returns(prices, args.cash, p.value()):.2f}%")
    if args.plot:
        plot_values(prices, [p.name for p in portfolios], values)
    
def main(): 
    yfcache = YFCache()
    
    # Process any cache related commands:
    if args.clear_cache:
        verbose(1, "Clearing cache")
        yfcache.clear()
    if args.update_cache:
        verbose(1, "Update cache...")
        yfcache.update()
    do_portfolios(yfcache)
    
if __name__ == "__main__":
    main()