#!/usr/bin/env python3


from yfcache import YFCache
from portfolio import Portfolio

ALLOC = {
    'GOOG': 0.1,
    'VTI': 0.5,
    'QQQ': 0.2,
}

yfcache = YFCache()

p = Portfolio(cash = 100000.0, yfcache = yfcache)
p.set_allocation(ALLOC)
prices = yfcache.join([symbol for symbol in ALLOC.keys()]).dropna()

for ds, row in prices.iterrows():
    print(f"{ds}")
    p.balance({
        symbol: row[symbol] for symbol in ALLOC.keys()
    })
