import math
from abc import ABC, abstractmethod
from typing import List, Mapping, Tuple

import matplotlib.pyplot as plt
import pandas as pd

from portfolio import Portfolio
from utils import as_timestamp
from yfcache import Quote, YFCache


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
    def execute(self, p: Portfolio, q: Quote):
        pass
            
    def run(self, p: Portfolio, q: Quote): 
        if q.timestamp in self.schedule and self.count != 0:
            self.execute(p, q)
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
        
    def execute(self, p: Portfolio, q: Quote):
        p.buy(self.symbol, self.quantity, q.timestamp)
            
class ClosePosition(Action):
    
    symbol: str
    
    def __init__(self, start: pd.Timestamp, freq: str, count: int,
                 symbol: str):
        super().__init__(start, freq, count)
        assert count > 0, "The number of steps in which to close position has to be positive."
        self.symbol = symbol
        
    def execute(self, p: Portfolio, q: Quote):
        position = p.position(self.symbol)        
        p.sell(self.symbol,
               position if self.count == 1 else int(position / self.count),
               q.timestamp)

class Balance(Action):
    
    alloc: Mapping[str, float]
    
    def __init__(self, start: pd.Timestamp, freq: str, 
                 alloc: Mapping[str, float]):
        super().__init__(start, freq, -1)
        self.alloc = alloc    
        
    def execute(self, p: Portfolio, q: Quote):
        print(f"{q.timestamp} Balance portfolio.")
        # Sell any issues that isn't in our allocation.
        for t in p.tickers():
            if self.alloc.get(t) is None:
                p.sell(t, p.position(t))
        # Perform the rebalancing.
        target_dollars = { ticker: p.value() * target for ticker, target in self.alloc.items() }
        for ticker, amount in target_dollars.items():
            diff = min(amount - p.get_holding(ticker), p.cash)
            quantity = int(math.floor(diff / p.price(ticker)))
            if quantity > 0:
                p.buy(ticker, quantity)
            else:
                p.sell(ticker, - quantity)

class Dividends(Action):
    
    def __init__(self):
        super().__init__(as_timestamp('1970-01-01'), 'B')
        
    def execute(self, p: Portfolio, q: Quote):
        for ticker in p.tickers():
            amount = q.Dividends(ticker) * p.position(ticker)
            if amount > 0:
                p.deposit(amount)
        
def plot_values(values: List[Tuple[ pd.Timestamp, float ]]):
    x, y = zip(*values)
    plt.plot(x, y)  #type: ignore
    plt.show()      #type: ignore
        
yfcache = YFCache()
reader = yfcache.reader(start_date=as_timestamp('2000-01-01'))
p = Portfolio(500000, name='Testing')

reader.require_all([ 'VTI', 'QQQ', 'GOOG'])

actions = [
    Dividends(),
    Buy(as_timestamp('2015-01-01'), 'BMS', 12, 'VTI', 100),
    Buy(as_timestamp('2016-01-01'), 'B', 12, 'GOOG', 100),
    ClosePosition(as_timestamp('2020-01-02'), 'W-MON', 52, 'VTI'),
    Balance(as_timestamp('2022-01-01'), 'BMS', alloc={ 'VTI': 0.4, 'QQQ': 0.6 })
]

values: List[ Tuple[pd.Timestamp, float] ] = []
for quote in reader.next():
    
    value = p.value(quote)
    for a in actions:
        a.run(p, quote)    
    values.append((quote.timestamp, value))
    
print(p)
plot_values(values)

    