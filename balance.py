#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false


from yfcache import YFCache
from portfolio import Portfolio

ALLOC = {
    'VTI': 0.8,
}

yfcache = YFCache()

p = Portfolio(cash = 10000.0)
p.set_allocation(ALLOC)
prices = yfcache.join([symbol for symbol in ALLOC.keys()]).dropna()

for ds, row in prices.iterrows():
    for op in p.balance({
        symbol: row[symbol] for symbol in ALLOC.keys()
    }):
        print(op)
print(p)

