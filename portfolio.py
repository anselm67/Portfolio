import json
import math
from enum import Enum
from typing import Dict, List, Optional, Self, Tuple

import pandas as pd

from utils import percent
from yfcache import Quote


class TradeOp(Enum):
    BUY = 1
    SELL = 2
    DEPOSIT = 3
    WITHDRAW = 4
    
    def __str__(self) -> str:
        return self.name
    

class LogEvent:
    
    def __init__(self, 
                 op: TradeOp,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0):
        self.op = op
        self.timestamp = timestamp
        self.commission = commission

    def __str__(self) -> str:
        return f"{self.timestamp} {self.op}"
        
class Buy(LogEvent):
    
    def __init__(self, symbol: str, quantity: int, price: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0):
        super().__init__(TradeOp.BUY, timestamp, commission)
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def __str__(self) -> str:
        return f"{self.timestamp} {self.op} {self.symbol} {self.quantity} @ {self.price:,.2f} = ${self.quantity * self.price:,.2f}"
        
class Sell(LogEvent):
    
    def __init__(self, symbol: str, quantity: int, price: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0):
        super().__init__(TradeOp.SELL, timestamp, commission)
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def __str__(self) -> str:
        return f"{self.timestamp} {self.op} {self.symbol} {self.quantity} @ {self.price:,.2f} = ${self.quantity * self.price:,.2f}"
        
class Deposit(LogEvent):
    
    def __init__(self, amount: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0):
        super().__init__(TradeOp.DEPOSIT, timestamp, commission)
        self.amount = amount
        
    def __str__(self) -> str:
        return f"{self.timestamp} {self.op} {self.amount:,.2f}"
        
class Withdraw(LogEvent):
    
    def __init__(self, amount: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0):
        super().__init__(TradeOp.WITHDRAW, timestamp, commission)
        self.amount = amount
        
    def __str__(self) -> str:
        return f"{self.timestamp} {self.op} {self.amount:,.2f}"

class Portfolio:
    _name: str
    _filename: Optional[ str ]
    _positions: Dict[str, int]
    _cash: float
    _alloc: Dict[str, float]
    quote: Quote 
    _cash_alloc: float
    
    def __init__(self, cash: float = 100000.0, name: Optional[ str ] = None):
        self._name = name or 'no name'
        self._filename = None
        self._cash = cash
        self._positions = { }
        self.quote = Quote.empty()
        self._alloc = { }
        self._cash_alloc = 1.0 

    def _check_prices(self):
        for symbol, _ in self._positions.items():
            assert self.quote.Close(symbol) is not None, f"{symbol} is not available in {self.quote.timestamp} quote."
        
    def set_quote(self, quote: Quote) -> Self:
        self.quote = quote
        return self
            
    def price(self, symbol: str) -> float:
        self._check_prices()
        return self.quote.Close(symbol)
    

    def buy(self, symbol: str, quantity: int, 
            timestamp: Optional[pd.Timestamp] = None,
            log: Optional[List[ LogEvent ]] = None) -> int:
        self._check_prices()
        self._positions[symbol] = self._positions.get(symbol, 0) + quantity
        self._cash -= (quantity * self.price(symbol))
        assert(self._cash >= 0.0)
        if log is not None:
            log.append(Buy(symbol, quantity, self.price(symbol), timestamp))
        return self._positions[symbol]

    def sell(self, symbol: str, quantity: int, 
             timestamp: Optional[pd.Timestamp] = None,
             log: Optional[List[ LogEvent ]] = None) -> int:
        self._check_prices()
        assert 0 <= quantity <= self._positions.get(symbol, 0), f"Invalid sell quantity for {symbol} {quantity}"
        self._positions[symbol] -= quantity
        self._cash += (quantity * self.price(symbol))
        if log is not None:
            log.append(Sell(symbol, quantity, self.price(symbol), timestamp))
        if self._positions[symbol] == 0:
            del self._positions[symbol]
            return 0
        else:
            return self._positions[symbol]
    
    @property
    def cash(self) -> float:
        return self._cash
    
    def deposit(self, amount: float, log: Optional[List[ LogEvent ]] = None) -> float:
        assert(amount > 0)
        self._cash += amount
        if log is not None:
            log.append(Deposit(amount))
        return self._cash
    
    def withdraw(self, amount: float, log: Optional[List[ LogEvent ]] = None) -> float:
        assert(amount > 0)
        self._cash -= amount
        if log is not None:
            log.append(Withdraw(amount))
        return self._cash

    @property
    def name(self) -> str:
        return self._name
    
    def set_position(self, symbol: str, quantity: int) -> Self:
        self._positions[symbol] = quantity
        return self
    
    def set_positions(self, positions: Dict[str, int]) -> Self:
        for k, v in positions.items():
            self.set_position(k, v)
        return self
            
    def position(self, symbol: str) -> int:
        return self._positions.get(symbol, 0)
        
    def tickers(self) -> List[ str ]:
        return list(self._positions.keys())
    
    def value(self, quote: Optional[Quote] = None) -> float:
        if quote is not None:
            self.set_quote(quote)
        self._check_prices()
        def ticker_value(symbol: str) -> float:
            return self.position(symbol) * self.price(symbol)
        return self._cash + sum(ticker_value(symbol) for symbol in self._positions.keys())
        
    def get_holding(self, symbol: str) -> float:
        self._check_prices()
        return self.price(symbol) * self.position(symbol)
    
    def set_allocation(self, alloc: Dict[str, float]) -> Self:
        new_alloc = { ticker: target for ticker, target in alloc.items() }
        cash_alloc = 1.0 - sum(new_alloc.values())
        assert(math.isclose(1.0, cash_alloc + sum(new_alloc.values())))
        self._alloc = new_alloc
        self._cash_alloc = cash_alloc
        return self
        
    def get_target_allocation(self, symbol: str) -> float:
        return self._alloc.get(symbol, 0)  
    
    def get_cash_allocation(self) -> float:
        return self._cash_alloc
    
    def balance(
        self, 
        quote: Quote,
        bounds: Tuple[float, float] = (0.2, 0.2),
    ) -> List[ LogEvent ]:
        log : List [ LogEvent ] = [ ]
        lower_bound, upper_bound = bounds
        self.set_quote(quote)
        alloc = { ticker: 0.0 for ticker in self._positions.keys() }
        for ticker in self._alloc.keys():
            alloc[ticker] = self.value() * self._alloc[ticker]
        for ticker, target in alloc.items():
            price = self.price(ticker)
            hold = price * self.position(ticker)
            if (1. - lower_bound) * target < hold < (1. + upper_bound) * target:
                continue
            order = int(math.floor(target / price) - self.position(ticker))
            if order > 0:
                self.buy(ticker, order, quote.timestamp, log)
            elif order < 0:
                self.sell(ticker, - order, quote.timestamp, log)
        # Rebalance the cash position if needed.
        target_cash = self._cash_alloc * self.value()
        extra_cash = self.cash - target_cash
        if (1. - lower_bound) * self.cash > target_cash or target_cash > (1. + upper_bound) * self.cash:            
            for ticker in alloc.keys():
                alloc[ticker] = extra_cash * (self._alloc[ticker] + self._cash_alloc / len(self._alloc))
            for ticker, target in alloc.items():
                price = self.price(ticker)
                order = int(math.floor(target / price))
                if order > 0:
                    self.buy(ticker, order, quote.timestamp, log)
                elif order < 0:
                    self.sell(ticker, - order, quote.timestamp, log)
        return log
    
    def __str__(self) -> str:
        value = self.value()
        text = f"{self.name} ${value:,.2f}\n\tCash: ${self._cash:,.2f}/{percent(self.cash, value)}%"
        for symbol, position in self._positions.items():
            holding = self.get_holding(symbol)
            text += f"\n\t{symbol}\t${holding:,.2f}/{position}/{percent(holding, value)}%"
        return text 
        
    @staticmethod
    def load(filename: str) -> "Portfolio":
        with open(filename, "r") as input:
            obj = json.load(input)
        p = Portfolio(obj.get('cash', 0))
        p._filename = filename
        p._name = obj.get('name', 'No Name')
        p.set_positions(obj.get('positions', {}))
        return p
        
    def save(self, filename: Optional[ str ] = None):
        if filename is None:
            filename = self._filename
            if filename is None:
                raise ValueError("No fiename for this portfolio.")
        with open(filename, "w+") as output:
            json.dump({
                "name": self._name,
                "cash": self.cash,
                "positions": self._positions
            }, output, indent=2)
        
