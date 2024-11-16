import json
from enum import Enum
from typing import Callable, Dict, List, Optional, Self

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
    
    op: TradeOp
    timestamp: Optional[ pd.Timestamp ]
    commission: float
    memo: str
    
    def __init__(self, 
                 op: TradeOp,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0,
                 memo: Optional [ str ] = None):
        self.op = op
        self.timestamp = timestamp
        self.commission = commission
        self.memo = memo or ''
        
    def display(self) -> str:
        return f"{self.timestamp} {self.op}"
        
class Buy(LogEvent):
    
    symbol: str
    quantity: int
    price: float 
    
    def __init__(self, symbol: str, quantity: int, price: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0,
                 memo: Optional [ str ] = None):
        super().__init__(TradeOp.BUY, timestamp, commission, memo)
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def display(self) -> str:
        return (
            f"{super().display()} "
            f"{self.symbol} {self.quantity} @ {self.price:,.2f} = "
            f"${self.quantity * self.price:,.2f} ({self.memo})"
        )
        
class Sell(LogEvent):
    
    def __init__(self, symbol: str, quantity: int, price: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0,
                 memo: Optional [ str ] = None):
        super().__init__(TradeOp.SELL, timestamp, commission, memo)
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def display(self) -> str:
        return (
            f"{super().display()} "
            f"{self.symbol} {self.quantity} @ {self.price:,.2f} = "
            f"${self.quantity * self.price:,.2f} ({self.memo})"
        )
        
class Deposit(LogEvent):
    
    def __init__(self, amount: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0,
                 memo: Optional [ str ] = None):
        super().__init__(TradeOp.DEPOSIT, timestamp, commission, memo)
        self.amount = amount
        
    def display(self) -> str:
        return (
            f"{super().display()} "
            f"${self.amount:,.2f} ({self.memo})"
        )
        
class Withdraw(LogEvent):
    
    def __init__(self, amount: float,
                 timestamp: Optional[ pd.Timestamp ] = None,
                 commission : float = 0,
                 memo: Optional [ str ] = None):
        super().__init__(TradeOp.WITHDRAW, timestamp, commission, memo)
        self.amount = amount
        
    def display(self) -> str:
        return (
            f"{super().display()} "
            "{self.amount:,.2f} ({self.memo})"
        )

class Portfolio:
    _name: str
    _filename: Optional[ str ]
    _positions: Dict[str, int]
    _cash: float
    quote: Quote 
    loggers: List[ Callable[[LogEvent], None]]
    
    def __init__(self, cash: float = 100000.0, name: Optional[ str ] = None):
        self._name = name or 'no name'
        self._filename = None
        self._cash = cash
        self._positions = { }
        self.quote = Quote.empty()
        self._alloc = { }
        self._cash_alloc = 1.0 
        self.loggers = []

    def _log(self, evt: LogEvent):
        for l in self.loggers:
            l(evt)
    
    def add_logger(self, logger: Callable[[LogEvent], None]):
        self.loggers.append(logger)
        
    def remove_logger(self, logger: Callable[[LogEvent], None]):
        self.loggers.remove(logger)

    def set_quote(self, quote: Quote) -> Self:
        self.quote = quote
        return self
            
    def price(self, symbol: str) -> float:
        return self.quote.Close(symbol)
    
    def buy(self, symbol: str, quantity: int, memo: Optional[ str ]=None) -> int:
        self._positions[symbol] = self._positions.get(symbol, 0) + quantity
        self._cash -= (quantity * self.price(symbol))
        assert(self._cash >= 0.0)
        self._log(Buy(symbol, quantity, self.price(symbol), self.quote.timestamp, memo=memo))
        return self._positions[symbol]

    def sell(self, symbol: str, quantity: int, memo: Optional[ str ]=None) -> int:
        assert 0 <= quantity <= self._positions.get(symbol, 0), f"Invalid sell quantity for {symbol} {quantity}"
        self._positions[symbol] -= quantity
        self._cash += (quantity * self.price(symbol))
        self._log(Sell(symbol, quantity, self.price(symbol), self.quote.timestamp, memo=memo))
        if self._positions[symbol] == 0:
            del self._positions[symbol]
            return 0
        else:
            return self._positions[symbol]
    
    @property
    def cash(self) -> float:
        return self._cash
    
    def deposit(self, amount: float, memo: Optional[ str ]=None) -> float:
        assert(amount > 0)
        self._cash += amount
        self._log(Deposit(amount, self.quote.timestamp, memo=memo))
        return self._cash
    
    def withdraw(self, amount: float, memo: Optional[ str ]=None) -> float:
        assert(amount > 0)
        self._cash -= amount
        self._log(Withdraw(amount, self.quote.timestamp, memo=memo))
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
        def ticker_value(symbol: str) -> float:
            return self.position(symbol) * self.price(symbol)
        return self._cash + sum(ticker_value(symbol) for symbol in self._positions.keys())
        
    def holding(self, symbol: str) -> float:
        return self.price(symbol) * self.position(symbol)
           
    def __str__(self) -> str:
        value = self.value()
        text = f"{self.name} ${value:,.2f}\n\tCash: ${self._cash:,.2f}/{percent(self.cash, value)}%"
        for symbol, position in self._positions.items():
            holding = self.holding(symbol)
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
        
