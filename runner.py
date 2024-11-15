import math
from abc import ABC, abstractmethod
from typing import List, Mapping, Tuple, cast

import matplotlib.pyplot as plt
import pandas as pd

from portfolio import Portfolio
from yfcache import YFCache


class Action(ABC):
    
    start: pd.Timestamp
    schedule: List[ pd.Timestamp ]
    count: int
        
    def __init__(self, start: pd.Timestamp, freq: str, count: int = -1):
        self.start = start
        assert count != 0, "The count N must be > 0 (to run N times) or -1 (to run for ever)."
        if count > 0:
            self.schedule = pd.date_range(
                start=start,
                freq=freq, periods=count, tz='UTC').date # type: ignore
            self.count = count
        else:
            self.schedule = pd.date_range(
                start=start, end=pd.Timestamp.now(tz='UTC'),
                freq=freq, tz='UTC').date # type: ignore
            self.count = -1
        
    @abstractmethod
    def execute(self, timestamp: pd.Timestamp, p: Portfolio):
        pass
            
    def run(self, timestamp: pd.Timestamp, p: Portfolio): 
        if timestamp in self.schedule and self.count != 0:
            self.execute(timestamp, p)
            if self.count > 0:
                self.count -= 1
        return p
            
class Buy(Action):
    
    symbol: str
    quantity: int
    
    def __init__(self, start: pd.Timestamp, freq: str, count: int,
                 symbol: str, quantity: int):
        super().__init__(start, freq, count)
        self.symbol = symbol
        self.quantity = quantity
        
    def execute(self, timestamp: pd.Timestamp, p: Portfolio):
        p.buy(self.symbol, self.quantity, timestamp)
            
class ClosePosition(Action):
    
    symbol: str
    
    def __init__(self, start: pd.Timestamp, freq: str, count: int,
                 symbol: str):
        super().__init__(start, freq, count)
        assert count > 0, "The number of steps in which to close position has to be positive."
        self.symbol = symbol
        
    def execute(self, timestamp: pd.Timestamp, p: Portfolio):
        position = p.position(self.symbol)        
        p.sell(self.symbol,
               position if self.count == 1 else int(position / self.count),
               timestamp)

class Balance(Action):
    
    alloc: Mapping[str, float]
    
    def __init__(self, start: pd.Timestamp, freq: str, 
                 alloc: Mapping[str, float]):
        super().__init__(start, freq, -1)
        self.alloc = alloc    
        
    def execute(self, timestamp: pd.Timestamp, p: Portfolio):
        print(f"{timestamp} Balance portfolio.")
        # Sell any issues that isn't in our allocation.
        for t in p.tickers():
            if self.alloc.get(t) is None:
                p.sell(t, p.position(t))
        # Perform the rebalancing.
        target_dollars = { ticker: p.value() * target for ticker, target in self.alloc.items() }
        for ticker, amount in target_dollars.items():
            diff = min(amount - p.get_holding(ticker), p.cash)
            quantity = int(math.floor(diff / p.get_price(ticker)))
            if quantity > 0:
                p.buy(ticker, quantity)
            else:
                p.sell(ticker, - quantity)

    
def plot_values(pd: pd.DataFrame, values: List[ float ]):
    plt.plot(pd.index, values)         # type: ignore
    plt.show()
        
yfcache = YFCache()
p = Portfolio(500000, name='Testing')

tickers = [
    'VTI', 'QQQ'
]

from_datetime = pd.Timestamp('2010-01-01', tz='UTC')
history = yfcache.join(tickers, from_datetime=from_datetime)

actions = [
    Buy(pd.Timestamp('2015-01-01', tz='UTC'), 'BMS', 12, 'VTI', 100),
    ClosePosition(pd.Timestamp('2020-01-02', tz='UTC'), 'W-MON', 52, 'VTI'),
    Balance(pd.Timestamp('2022-01-01', tz='UTC'), 'BMS', alloc={ 'VTI': 0.4, 'QQQ': 0.6 })
]

values: List[ float ] = []
for timestamp, row in history.iterrows():
    row = cast(Mapping[Tuple[str, str], float], row)
    timestamp = cast(pd.Timestamp, timestamp)
    
    value = p.value({
        symbol: row[symbol, 'Close'] for symbol in tickers
    })
    for a in actions:
        a.run(timestamp, p)    
    values.append(value)
    
print(p)
plot_values(history, values)

    