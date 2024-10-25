from typing import Dict, Tuple
from pathlib import Path
import pickle

import yfinance as yf
import pandas as pd

class YFTicker:
    
    symbol: str
    first_trade: int
    history: pd.DataFrame
    
    def __init__(self, ticker: yf.Ticker):
        self.symbol = ticker.ticker
        self.first_trade = ticker.history_metadata['firstTradeDate']
        self.history = ticker.history(period='max')
        
    def __getstate__(self):
        return self.__dict__.copy()
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        
    def last_price(self) -> float:
        return self.history.iloc[-1].Close
    
class YFCache:
    CACHEDIR = 'cache'
    
    directory: str
    cache: Dict[str, YFTicker]
    
    @staticmethod
    def norm(symbol: str) -> str:
        return symbol.upper()
    
    def __init__(self, directory = CACHEDIR):
        self.directory = directory
        self.cache = { }
        Path(directory).mkdir(parents = True, exist_ok = True)
        
    def __path(self, symbol: str) -> Path:
        return Path(self.directory, f"{symbol}.pkl")

    def __fetch(self, symbol: str) -> YFTicker:
        yfticker = YFTicker(yf.Ticker(symbol))
        with open(self.__path(symbol), "wb") as output:
            pickle.dump(yfticker, output)
        return yfticker
        
    def __load(self, symbol: str) -> YFTicker:
        path = self.__path(symbol)
        if path.exists():
            with open(self.__path(symbol), "rb") as input:
                yfticker = pickle.load(input)
        else:
            yfticker = self.__fetch(symbol)
        self.cache[symbol] = yfticker
        return yfticker
    
    def get_ticker(self, symbol: str) -> YFTicker:
        symbol = YFCache.norm(symbol)
        yfticker = self.cache.get(symbol)
        if yfticker is None:
            yfticker = self.__load(symbol)
        return yfticker
            
    
        
        
