# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

import os
import pickle
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf  # type: ignore


class YFTicker:
    
    first_trade: pd.Timestamp
    history: Any
    history_metadata: Any
    
    def __init__(self, ticker: yf.Ticker):
        self.first_trade = pd.to_datetime(ticker.history_metadata['firstTradeDate'], unit='s') \
            .tz_localize(ticker.history_metadata['timezone']) 
        self.history = ticker.history(period='max').tz_convert('UTC') 
        self.history_metadata = ticker.history_metadata
        
    @property
    def symbol(self):
        return self.history_metadata['symbol']
        
    @property
    def daily_history(self):
        data = self.history.copy()
        data.index = data.index.date
        return data
    
    def __getstate__(self):
        return self.__dict__.copy()
    
    def __setstate__(self, state: Any):
        self.__dict__.update(state)
        
    def last_price(self) -> float:
        return self.history.iloc[-1].Close # type: ignore
    
class YFCache:
    CACHEDIR = 'cache'
    
    directory: str
    cache: Dict[str, YFTicker]
    
    @staticmethod
    def norm(symbol: str) -> str:
        return symbol.upper()
    
    def __init__(self, directory: str = CACHEDIR):
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
    
    def clear(self):
        for file in os.listdir(self.directory):
            path = Path(self.directory, file)
            if os.path.isfile(path):
                os.remove(path)
            
    def update(self):
        tickers = [Path(file).stem for file in os.listdir(self.directory)]
        for ticker in tickers:
            os.remove(self.__path(ticker))
        for ticker in tickers:
            self.get_ticker(ticker)
        
    def get_ticker(self, symbol: str) -> YFTicker:
        symbol = YFCache.norm(symbol)
        yfticker = self.cache.get(symbol)
        if yfticker is None:
            yfticker = self.__load(symbol)
        return yfticker
            
    def start_date(self, tickers: List[ str ]) -> pd.Timestamp:
        date = reduce(lambda x, y: max(x, y), [self.get_ticker(t).first_trade for t in tickers])
        return date.tz_convert('UTC')
        
    def join(self, 
             symbols: List[ str ], 
             from_datetime: Optional[pd.Timestamp] = None, 
             till_datetime: Optional[pd.Timestamp] = None) -> pd.DataFrame:
        tickers = [self.get_ticker(x) for x in symbols]
        from_datetime = from_datetime or min(t.history.index.min() for t in tickers)
        till_datetime = till_datetime or max(t.history.index.max() for t in tickers)
        index: Any = pd.date_range(start=from_datetime, end=till_datetime, freq='B', tz='UTC').date
        df = pd.concat({ 
            t.symbol: t.daily_history.reindex(index) for t in tickers  
        }, axis=1, keys=symbols)
        df.ffill(inplace=True)
        df.fillna(0, inplace=True)
        return df 
    
        
        
        
