from typing import Tuple, List, Dict, Self, Optional
from enum import Enum

from yfcache import YFCache

import math

class TradeOp(Enum):
    BUY = 1,
    SELL = 2
    
class Trade:
    
    def __init__(self, 
                 op: TradeOp, quantity: int, price: float, 
                 commission : float = 0):
        self.op = op
        self.quantity = quantity
        self.price = price
        self.commission = commission
        
    def __str__(self) -> str:
        return f"{self.op} {self.quantity} @ {self.price:,.2f} = ${self.quantity * self.price:,.2f}"
        
        
class Portfolio:
    _positions: Dict[str, int]
    _cash: float
    _alloc: Dict[str, float]
    _prices: Dict[str, float]
    _cash_alloc: float
    
    def __init__(self, cash: float = 100000.0):
        self._cash = cash
        self._positions = { }
        self._prices = { }
        self._alloc = { }
        self._cash_alloc = 1.0 

    @staticmethod
    def norm(symbol: str) -> str :
        return YFCache.norm(symbol)
    
    def _check_prices(self):
        for symbol, _ in self._positions.items():
            if self._prices.get(symbol) is None:
                raise AssertionError(f"No price for {symbol}")
        
    def set_prices(self, prices: Dict[str, float]) -> Self:
        self._prices = { self.norm(symbol): price for symbol, price in prices.items() } 
        return self
    
    def update_prices(self, prices: Dict[str, float]) -> Self:
        self._prices.update(prices)
        return self
        
    def buy(self, symbol: str, quantity: int, log: Optional[List[ Trade ]] = None) -> int:
        symbol = Portfolio.norm(symbol)
        self._check_prices()
        self._positions[symbol] = self._positions.get(symbol, 0) + quantity
        self._cash -= (quantity * self._prices[symbol])
        assert(self._cash >= 0.0)
        if log is not None:
            log.append(Trade(TradeOp.BUY, quantity, self._prices[symbol]))
        return self._positions[symbol]

    def sell(self, symbol: str, quantity: int, log: Optional[List[ Trade ]] = None) -> int:
        symbol = Portfolio.norm(symbol)
        self._check_prices()
        assert(quantity <= self._positions.get(symbol, 0))
        self._positions[symbol] -= quantity
        self._cash += (quantity * self._prices[symbol])
        if log is not None:
            log.append(Trade(TradeOp.SELL, quantity, self._prices[symbol]))
        if self._positions[symbol] == 0:
            del self._positions[symbol]
            return 0
        else:
            return self._positions[symbol]
    
    @property
    def cash(self) -> float:
        return self._cash
    
    def set_cash(self, cash: float) -> Self:
        self._cash = cash
        return self
    
    def set_position(self, symbol: str, quantity: int) -> Self:
        self._positions[self.norm(symbol)] = quantity
        return self
    
    def set_positions(self, positions: Dict[str, int]) -> Self:
        for k, v in positions.items():
            self.set_position(k, v)
        return self
            
    def position(self, symbol: str) -> float:
        symbol = Portfolio.norm(symbol)
        return self._positions.get(symbol, 0)
        
    @property
    def value(self) -> float:
        self._check_prices()
        def ticker_value(symbol: str) -> float:
            return self.position(symbol) * self._prices[symbol]
        return self._cash + sum(ticker_value(symbol) for symbol in self._positions.keys())
        
    def get_holding(self, symbol: str) -> float:
        self._check_prices()
        return self._prices[symbol] * self.position(symbol)
    
    def set_allocation(self, alloc: Dict[str, float]) -> Self:
        new_alloc = { self.norm(ticker): target for ticker, target in alloc.items() }
        cash_alloc = 1.0 - sum(new_alloc.values())
        assert(math.isclose(1.0, cash_alloc + sum(new_alloc.values())))
        self._alloc = new_alloc
        self._cash_alloc = cash_alloc
        return self
        
    def get_target_allocation(self, symbol: str) -> float:
        return self._alloc.get(self.norm(symbol), 0)  
    
    def get_cash_allocation(self) -> float:
        return self._cash_alloc
    
    def balance(
        self, 
        prices: Dict[str, float],
        bounds: Tuple[float, float] = (0.2, 0.2),
    ) -> List[ Trade ]:
        log : List [ Trade ] = [ ]
        lower_bound, upper_bound = bounds
        self.update_prices(prices)
        alloc = { ticker: 0.0 for ticker in self._positions.keys() }
        for ticker in self._alloc.keys():
            alloc[ticker] = self.value * self._alloc[ticker]
        for ticker, target in alloc.items():
            price = prices[ticker]
            hold = price * self.position(ticker)
            if (1. - lower_bound) * target < hold < (1. + upper_bound) * target:
                continue
            order = int(math.floor(target / price) - self.position(ticker))
            if order > 0:
                self.buy(ticker, order, log)
            elif order < 0:
                self.sell(ticker, - order, log)
        # Rebalance the cash position if needed.
        target_cash = self._cash_alloc * self.value
        extra_cash = self.cash - target_cash
        if (1. - lower_bound) * self.cash > target_cash or target_cash > (1. + upper_bound) * self.cash:            
            for ticker in alloc.keys():
                alloc[ticker] = extra_cash * (self._alloc[ticker] + self._cash_alloc / len(self._alloc))
            for ticker, target in alloc.items():
                price = prices[ticker]
                order = int(math.floor(target / price))
                if order > 0:
                    self.buy(ticker, order, log)
                elif order < 0:
                    self.sell(ticker, - order, log)
        return log
    
    def __str__(self) -> str:
        value = self.value
        text = f"${value:,.2f} [Cash: ${self._cash:,.2f}/{100.0 * self._cash / value:.2f}%"
        sep = " "
        for symbol, position in self._positions.items():
            holding = self.get_holding(symbol)
            text += f"{sep}{symbol}: ${holding:,.2f}/{position}/{100.0 * holding / value:.2f}%"
            sep = ", "
        return text + "]"
        
    
