from typing import Dict, Self
from yfcache import YFCache

import math

class Portfolio:
    CASH_SYMBOL = '$$CASH'
    
    _positions: Dict[str, int]
    _cash: float
    _alloc: Dict[str, float]
    _prices: Dict[str, float]
    
    def __init__(self, cash: float = 100000.0):
        self._cash = cash
        self._positions = { }
        self._prices = { }
        self._alloc = { self.CASH_SYMBOL: 1.0 }

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
        
    def buy(self, symbol, quantity: int) -> int:
        symbol = Portfolio.norm(symbol)
        self._check_prices()
        self._positions[symbol] = self._positions.get(symbol, 0) + quantity
        self._cash -= (quantity * self._prices[symbol])
        assert(self._cash >= 0.0)
        return self._positions[symbol]

    def sell(self, symbol, quantity) -> int:
        symbol = Portfolio.norm(symbol)
        self._check_prices()
        assert(quantity <= self._positions.get(symbol, 0))
        self._positions[symbol] -= quantity
        self._cash += (quantity * self._prices[symbol])
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
    
    def set_position(self, symbol, quantity) -> Self:
        self._positions[self.norm(symbol)] = quantity
        return self
    
    def set_positions(self, positions: Dict[str, int]) -> Self:
        for k, v in positions:
            self.set_position(k, v)
        return self
            
    def position(self, symbol: str) -> float:
        symbol = Portfolio.norm(symbol)
        return self._positions.get(symbol, 0)
        
    def value(self) -> float:
        self._check_prices()
        def ticker_value(symbol) -> float:
            return self.position(symbol) * self._prices[symbol]
        return self._cash + sum(ticker_value(symbol) for symbol in self._positions.keys())
        
    def get_holding(self, symbol: str) -> float:
        self._check_prices()
        return self._prices[symbol] * self.position(symbol)
    
    def set_allocation(self, alloc: Dict[str, float]) -> Self:
        new_alloc = { self.norm(ticker): target for ticker, target in alloc.items() }
        if self.CASH_SYMBOL not in new_alloc:
            new_alloc[self.CASH_SYMBOL] = 1.0 - sum(new_alloc.values())
        assert(math.isclose(1.0, sum(new_alloc.values())))
        self._alloc = new_alloc
        return self
        
    def get_target_allocation(self, symbol: str) -> float:
        return self._alloc.get(self.norm(symbol), 0)  
    
    def balance(self, prices: Dict[str, float]) -> Self:
        self.update_prices(prices)
        lower_bound, upper_bound = 0.1, 0.1
        value = self._cash + sum(self.position(ticker) * prices[ticker] for ticker in self._positions)
        alloc = { ticker: 0.0 for ticker in self._positions.keys() }
        for ticker in self._alloc.keys():
            alloc[ticker] = value * self._alloc[ticker]
        for ticker, target in alloc.items():
            if ticker == self.CASH_SYMBOL: 
                continue
            price = prices[ticker]
            hold = price * self.position(ticker)
            if (1. - lower_bound) * target < hold < (1. + upper_bound) * target:
                continue
            order = int(math.floor(target / price) - self.position(ticker))
            if order > 0:
                self.buy(ticker, order)
            elif order < 0:
                self.sell(ticker, - order)
            print(f"{"B" if order > 0 else "S"} {ticker}: {order} @ {price}")
        return self
    
    def __str__(self) -> str:
        value = self.value()
        text = f"${value:,.2f} [{self.CASH_SYMBOL}: ${self._cash:,.2f}/{100.0 * self._cash / value:.2f}%"
        sep = " "
        for symbol, position in self._positions.items():
            holding = self.get_holding(symbol)
            text += f"{sep}{symbol}: {position}@${holding:,.2f}/{100.0 * holding / value:.2f}%"
            sep = ", "
        return text + "]"
        
    
