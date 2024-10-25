from typing import Dict, Self
from yfcache import YFCache

import math

class Portfolio:
    CASH_SYMBOL = '$$CASH'
    
    _positions: Dict[str, int]
    _cash: float
    _yfcache: YFCache

    def __init__(self, cash: float = 100000.0, yfcache = YFCache()):
        self._cash = cash
        self._yfcache = yfcache
        self._positions = { }
        self.alloc = { self.CASH_SYMBOL: 1.0 }

    @staticmethod
    def norm(symbol: str) -> str :
        return YFCache.norm(symbol)
    
    def buy(self, symbol, quantity: int, price: float) -> int:
        symbol = Portfolio.norm(symbol)
        self._positions[symbol] = self._positions.get(symbol, 0) + quantity
        self._cash -= (quantity * price)
        assert(self._cash >= 0.0)
        return self._positions[symbol]

    def sell(self, symbol, quantity, price) -> int:
        symbol = Portfolio.norm(symbol)
        assert(quantity <= self._positions.get(symbol, 0))
        self._positions[symbol] -= quantity
        self._cash += (quantity * price)
        if self._positions[symbol] == 0:
            del self._positions[symbol]
            return 0
        else:
            return self._positions[symbol]

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
    
    def cash(self) -> float:
        return self._cash
    
    def value(self) -> float:
        def ticker_value(ticker) -> float:
            return self.position(ticker) * self._yfcache.get_ticker(ticker).last_price()
        return self._cash + sum(ticker_value(ticker) for ticker in self._positions.keys())
        
    def set_allocation(self, alloc: Dict[str, float]) -> Self:
        if self.CASH_SYMBOL not in alloc:
            alloc[self.CASH_SYMBOL] = 1.0 - sum(alloc.values())
        assert(math.isclose(1.0, sum(alloc.values())))
        self.alloc = { self.norm(ticker): target for ticker, target in alloc.items() }
        return self
        
    def get_target_allocation(self, symbol: str) -> float:
        return self.alloc.get(self.norm(symbol), 0)  
    
    def balance(self, prices: Dict[str, float]) -> Self:
        value = self._cash + sum(self.position(ticker) * prices[ticker] for ticker in self._positions)
        alloc = { ticker: 0.0 for ticker in self._positions.keys() }
        for ticker in self.alloc.keys():
            alloc[ticker] = value * self.alloc[ticker]
        print(alloc)
        for ticker, target in alloc.items():
            if ticker == self.CASH_SYMBOL: 
                continue
            price = prices[ticker]
            order = int(math.floor(target / price) - self.position(ticker))
            if order > 0:
                self.buy(ticker, order, price)
            elif order < 0:
                self.sell(ticker, - order, price)
            print(f"{"B" if order > 0 else "S"} {ticker}: {order} @ {price}")
        return self
    
