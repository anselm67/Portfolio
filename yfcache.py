# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

import os
import pickle
from functools import reduce
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, cast

import pandas as pd
import yfinance as yf  # type: ignore

from utils import as_timestamp  # type: ignore


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
    START_DATE = as_timestamp('1975-01-01')
    
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
        
    def reader(self, 
               start_date: Optional[ pd.Timestamp ] = None,
               end_date: Optional[pd.Timestamp] = None) -> 'Reader':
        """Create a reader to obtain a stream of quotes.

        Args:
            start_date (pd.Timestamp): Starting date of the stream of quotes.
            end_date (Optional[pd.Timestamp], optional): Ending date, defaults to today.

        Returns:
            Reader: A Reader instance that will provide a stream of daily Quote for the
            given date range.
        """
        if start_date is None:
            start_date = YFCache.START_DATE
        if end_date is None:
            end_date = pd.Timestamp.now(tz='UTC')
        return Reader(self, start_date, end_date)
    
class Quote:
    
    timestamp: pd.Timestamp
    values: Mapping[Tuple[str, str], float]

    @staticmethod
    def empty() -> 'Quote':
        return Quote(as_timestamp('1970-01-01'), { })    
    
    @staticmethod
    def from_dataframe(row: pd.DataFrame): 
        return Quote(cast(pd.Timestamp, row.name), 
                     cast(Mapping[Tuple[str, str], float], row))
        
    def __init__(self, timestamp: pd.Timestamp, data: Mapping[Tuple[str, str], float]):
        self.timestamp = timestamp
        self.values = data
        
    def Close(self, symbol: str) -> float:
        return self.values[symbol, 'Close']
    
    def Dividends(self, symbol: str) -> float:
        return self.values[symbol, 'Dividends']
    
class Reader:
        
    yfcache: YFCache
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    required: set[ str ]
    dataframe: Optional[ pd.DataFrame ]
    position: int
    
    def __init__(self, yfcache: YFCache, start_date: pd.Timestamp, end_date: pd.Timestamp):
        self.yfcache = yfcache
        self.start_date = start_date
        self.end_date = end_date
        self.required = set()
        self.dirty = True
        self.dataframe = None
        self.position = 0
        
    def require(self, symbol: str):
        if symbol in self.required:
            return
        # Recompose the data frame with this new symbol
        self.required.add(symbol)
        self.dirty = True
        
    def require_all(self, symbols: List [ str ]):
        for s in symbols:
            self.require(s)
            
    def update(self):
        tickers = [self.yfcache.get_ticker(x) for x in self.required]
        index: Any = pd.date_range(
            start=self.start_date, 
            end=self.end_date, 
            freq='B', tz='UTC').date
        df = pd.concat({ 
            t.symbol: t.daily_history.reindex(index) for t in tickers  
        }, axis=1, keys=self.required)
        df.ffill(inplace=True)
        df.fillna(0, inplace=True)
        self.dirty = False
        self.dataframe = df
        return df 
            
    def get_dataframe(self) -> pd.DataFrame:
        if self.dirty:
            self.update()
        return cast(pd.DataFrame, self.dataframe)
    
    def __iter__(self) -> Iterator['Quote']:
        return self
    
    def __next__(self) -> 'Quote':
        df = self.get_dataframe()
        while self.position < len(df):
            row = df.iloc[self.position]     # type: ignore
            self.position += 1
            return Quote.from_dataframe(cast(pd.DataFrame ,row))
        raise StopIteration
        

        
    
        
        
        
