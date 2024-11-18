#!/usr/bin/env python3

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
    freq: str
    count: int
        
    def __init__(self, start: pd.Timestamp, freq: str, count: int = -1):
        self.start = start
        self.freq = freq
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
        if count <= 0:
            self.quantity = quantity
        else:
            self.quantity = int(math.floor(quantity / count))
        
    def execute(self, p: Portfolio, q: Quote):
        p.buy(self.symbol, self.quantity)
            
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
               position if self.count == 1 else int(position / self.count))

class Balance(Action):
    
    alloc: Mapping[str, float]
    cash_alloc: float
    bounds: Tuple[float, float]
    
    def __init__(self, start: pd.Timestamp, freq: str, 
                 alloc: Mapping[str, float]):
        super().__init__(start, freq, -1)
        self.alloc = alloc    
        self.bounds = (0, 0)
        self.cash_alloc = 1. - sum(alloc.values())
        assert self.cash_alloc >= 0, "Sum of allocation exceeds 100%"

    def balance(self, p: Portfolio, q: Quote, targets: Mapping[str, float]):        
        for ticker, target in targets.items():
            # Checks whether we're outside out bounds. (0 ,0) bounds always trigger.
            hold = p.holding(ticker)
            if (1. - self.bounds[0]) * target < hold < (1. + self.bounds[1]) * target:
                continue
            # Performs the rebalanmcing operation.
            if target > hold:
                quantity = int(math.floor(min(target - hold, p.cash) / p.price(ticker)))
                if quantity > 0:
                    p.buy(ticker, quantity, memo='Rebalancing')
            else:
                quantity = int(math.floor((hold - target) / p.price(ticker)))
                if quantity > 0:
                    p.sell(ticker, quantity, memo='Rebalancing')
        
        
    def execute(self, p: Portfolio, q: Quote):
        # Sell any issues that isn't in our allocation.
        for t in p.tickers():
            if self.alloc.get(t) is None:
                p.sell(t, p.position(t))
        # Performs the stock and cash rebalancing.
        self.balance(p, q, { ticker: p.value() * target for ticker, target in self.alloc.items() })
        cash_target = self.cash_alloc * p.value()
        if (1. - self.bounds[0]) * p.cash > cash_target or cash_target > (1. + self.bounds[1]) * p.cash:
            extra_cash = p.cash - cash_target 
            for ticker, target in self.alloc.items():
                amount = extra_cash * (target + self.cash_alloc / len(self.alloc))
                quantity = int(math.floor(amount / p.price(ticker)))
                if quantity > 0:
                    p.buy(ticker, quantity, memo='Cash rebalancing')


class Dividends(Action):
    
    def __init__(self):
        super().__init__(YFCache.START_DATE, 'B')
        
    def execute(self, p: Portfolio, q: Quote):
        for ticker in p.tickers():
            dividends = q.Dividends(ticker)
            if dividends > 0:
                p.deposit(dividends * p.position(ticker),
                          memo=f"{ticker} dividends of ${dividends} x {p.position(ticker):,}")
        
class Deposit(Action):
    
    amount: float
    
    def __init__(self, start: pd.Timestamp, freq: str, count: int = -1, amount: float = 0.0):
        super().__init__(start, freq, count)
        if count < 0:
            # Deposit a given amount for ever.
            self.amount = amount
        else:
            # Deposit a given amount over COUNT deposits.
            self.amount = amount / count
    
    def execute(self, p: Portfolio, q: Quote):
        p.deposit(self.amount)
            
class Withdraw(Action):
    
    amount: float
    
    def __init__(self, start: pd.Timestamp, freq: str, count: int = -1, amount: float = 0.0):
        super().__init__(start, freq, count)
        if count < 0:
            # Deposit agiven amount for ever.
            self.amount = amount
        else:
            # Deposit a given amount over COUNT deposits.
            self.amount = amount / count
    
    def execute(self, p: Portfolio, q: Quote):
        p.withdraw(self.amount)
         
class CashInterest(Action):
    
    monthly_rate: float
    
    def __init__(self, yearly_rate: float):
        super().__init__(YFCache.START_DATE, 'BMS')
        self.monthly_rate = yearly_rate / 12
        
    def execute(self, p: Portfolio, q: Quote):
        amount = self.monthly_rate * p.cash
        if amount > 0:
            p.deposit(amount, memo='Monthly cash interest rate.')
        
        
def plot_values(values: List[Tuple[ pd.Timestamp, float ]]):
    x, y = zip(*values)
    plt.plot(x, y)  #type: ignore
    plt.show()      #type: ignore
        
def main():
    yfcache = YFCache()
    reader = yfcache.reader(start_date=as_timestamp('2000-01-01'))
    portfolio = Portfolio(500000, name='Testing')
    portfolio.add_logger(lambda e: print(e.display()))
    
    reader.require_all([ 'VTI', 'QQQ', 'GOOG'])

    actions = [
        Dividends(),
        CashInterest(0.05),
        Buy(as_timestamp('2015-01-01'), 'BMS', 12, 'VTI', 100),
        Buy(as_timestamp('2016-01-01'), 'B', 12, 'GOOG', 100),
        ClosePosition(as_timestamp('2020-01-02'), 'W-MON', 52, 'VTI'),
        Balance(as_timestamp('2022-01-01'), 'BMS', alloc={ 'VTI': 0.4, 'QQQ': 0.6 })
    ]

    values: List[ Tuple[pd.Timestamp, float] ] = []

    for quote in reader:    
        value = portfolio.value(quote)
        for a in actions:
            a.run(portfolio, quote)    
        values.append((quote.timestamp, value))
        
    print(portfolio)
    plot_values(values)

if __name__ == '__main__':
    main()