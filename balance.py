#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false


from portfolio import Portfolio
from yfcache import YFCache

ALLOC = {
    'GOOG': 0.2,
    'VTI': 0.6,
}

yfcache = YFCache()

p = Portfolio(cash = 10000.0)
p.set_allocation(ALLOC)
prices = yfcache.join([symbol for symbol in ALLOC.keys()]).dropna()
bounds = (0.25, 0.25)

for timestamp, row in prices.iterrows():
    for op in p.balance({
        symbol: row[symbol] for symbol in ALLOC.keys()
    }, bounds, timestamp):  # type: ignore
        print(op)
print(p)

