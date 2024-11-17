#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

import argparse
import datetime
import math
import sys
from typing import Any, List, Optional, Sequence, Set, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from actions import Action, Balance, CashInterest, Dividends
from portfolio import Portfolio
from utils import as_timestamp, dollars
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

class RepeatableTwoArgsAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: Optional[str] = None,
    ) -> None:
        # Initialize the attribute as a list if it does not exist
        if getattr(namespace, self.dest) is None:
            setattr(namespace, self.dest, [])
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError(f"Expected exactly 2 arguments for {option_string}, got {values}")
        # Append the tuple of values
        getattr(namespace, self.dest).append(tuple(values))
        
parser = argparse.ArgumentParser(
    prog='balance.py',
    description="Explores a rebalancing strategy."
)
parser.add_argument('-p', '--portfolio', nargs=2, action=RepeatableTwoArgsAction,
                    metavar=('portfolio.json', 'program.txt'),
                    help='Json portfolio file.')
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help='Chat some as we procceed.')
parser.add_argument('--from', type=datetime.date.fromisoformat, default=None,
                    dest='from_datetime',
                    help='Restrict analysis to data later than this date (YYYY-MM-DD)')
parser.add_argument('--till', type=datetime.date.fromisoformat, default=None,
                    dest='till_datetime',
                    help='Restrict analysis to data earlier than this date (YYYY-MM-DD)')
parser.add_argument('--auto-start', action='store_true',default=False,
                    help='Start analysis on the first day where all tickers exist.')
parser.add_argument('--plot', action='store_true', default=False,
                    help='Plot portfolio values by dates.')
# Cache related commands
parser.add_argument('--clear-cache', action='store_true', default=False,
                    help='Clears the ticker cache.')
parser.add_argument('--update-cache', action='store_true', default=False,
                    help='Updates the cache with the freshest stock quotes.')

DEBUG_ARGS = [
    '-p', 'portfolios/ira.json', 'dividends',
    '-p', 'portfolios/main.json', 'full',
    '--plot', '--auto-start', '-v'
]
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

def plot_values(chronology: List[pd.Timestamp], 
                names: List[ str ], 
                values: List[ List[ float ] ]):
    def formatter(value: float, _: float) -> str:
        return dollars(value)
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('time')
    ax1.set_ylabel('Position', color='tab:blue')
    for n, v in zip(names, values):
        ax1.plot(chronology, v, label=n)         # type: ignore
    fig.tight_layout()
    ax1.yaxis.set_major_formatter(FuncFormatter(formatter))
    plt.legend(title='Portfolios')
    plt.show()

def get_actions(actions_name: str) -> List[ Action ]:
    if actions_name == 'dividends':
        return [
            Dividends(),
        ]
    elif actions_name == 'full':
       return [
            Dividends(),
            CashInterest(0.05),
            Balance(as_timestamp('2022-01-01'), 'BMS', alloc={ 'VTI': 0.4, 'QQQ': 0.6 })
        ]
    elif actions_name == 'noop':
        return [ ]
    else:
        raise ValueError(f"{actions_name} program not found.")
    
def do_portfolios(yfcache: YFCache):
    if len(args.portfolio) == 0:
        return
    portfolios = [(Portfolio.load(p), get_actions(a)) for (p, a) in args.portfolio]
    # Compute the set of unique tickers within the portfolio
    tickers: Set[ str ] = set()
    for p, _ in portfolios:
        p.add_logger(lambda evt: print(f"{p.name}: {evt.display()}"))
        tickers.update(p.tickers())
    # Computes the start date of the analysis, None allowed.
    from_datetime = None
    if args.auto_start:
        from_datetime = yfcache.start_date(list(tickers))
        verbose(1, f"Starting analysis on {from_datetime}")
    elif args.from_datetime is not None:
        from_datetime = pd.Timestamp(args.from_datetime).tz_localize('UTC')
    # Line up the prices of all requested issues.
    reader = yfcache.reader(start_date=from_datetime,
                            end_date=args.till_datetime)
    reader.require_all(list(tickers))
    
    values: List[ List[float] ] = [ [].copy() for _ in portfolios ]
    chronology: List[ pd.Timestamp ] = []
    for quote in reader:
        for (p, actions), v in zip(portfolios, values):
            v.append(p.value(quote))
            for a in actions:
                a.run(p, quote)
        chronology.append(quote.timestamp)
        
    for (p, _), v in zip(portfolios, values):
        print(p)
#        print(f"Annual returns: {annual_returns(prices, args.cash, p.value()):.2f}%")
    if args.plot:
        plot_values(chronology, [p.name for p, _ in portfolios], values)
    
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