from typing import Dict

class Portfolio:
    stocks: Dict[str, int]
    cash: float

    def __init__(self, cash: float = 100000.0):
        self.cash = cash
        self.stocks = { }

    @staticmethod
    def norm(symbol: str):
        return symbol.upper()
    
    def buy(self, symbol, quantity: int, price: float):
        symbol = Portfolio.norm(symbol)
        self.stocks[symbol] = self.stocks.get(symbol, 0) + quantity
        self.cash -= (quantity * price)
        assert(self.cash >= 0.0)
        return self.stocks[symbol]

    def sell(self, symbol, quantity, price):
        symbol = Portfolio.norm(symbol)
        assert(quantity <= self.stocks.get(symbol, 0))
        self.stocks[symbol] -= quantity
        if self.stocks[symbol] == 0:
            del self.stocks[symbol]
        self.cash += (quantity * price)

    def position(self, symbol: str):
        symbol = Portfolio.norm(symbol)
        return self.stocks.get(symbol, 0)


    
    