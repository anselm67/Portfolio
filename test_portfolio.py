import unittest
from typing import Mapping

import pandas as pd

from portfolio import Portfolio
from runner import Balance
from utils import as_timestamp
from yfcache import Quote


def make_quote(data: Mapping[str, float]) -> 'Quote':
    return Quote(pd.Timestamp.now(tz='UTC'), {
        (ticker, 'Close'): value for ticker, value in data.items()
    })

class TestPortfolio(unittest.TestCase):
  
    def test_default_cash(self):
        p = Portfolio()
        self.assertEqual(p.cash, 100000.0)
        self.assertAlmostEqual(p.value(), 100000.0)

    def test_buy(self):
        p = Portfolio()
        self.assertEqual(p.cash, 100000.0)
        p.set_quote(make_quote({ 'vti': 100.0 }))
        p.buy('vti', 10)
        self.assertEqual(p.cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)

    def test_sell_none(self):
        p = Portfolio()
        p.set_quote(make_quote({ 'vti': 100.0 }))
        self.assertRaises(AssertionError, p.sell, 'vti', 10)

    def test_sell_toomany(self):
        p = Portfolio()
        p.set_quote(make_quote({ 'vti': 100.0 }))
        p.buy('vti', 10)
        self.assertRaises(AssertionError, p.sell,'vti', 11)

    def test_sell(self):
        p = Portfolio()
        p.set_quote(make_quote({ 'vti': 100.0 }))
        self.assertEqual(p.cash, 100000.0)
        p.buy('vti', 10)
        self.assertEqual(p.cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)
        p.sell('vti', 10)
        self.assertEqual(p.cash, 100000.0)
        
    def test_rebalance1(self):
        quote = make_quote({
            'VTI': 100.0,
            'GOOG': 20.0,
        })
        p = Portfolio()
        p.set_quote(quote)
        Balance(as_timestamp('2024-01-1'), 'B', {
            'VTI': 0.5,
            'GOOG': 0.2
        }).execute(p, quote)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(1000, p.position('GOOG'))
        self.assertAlmostEqual(30000.0, p.cash)
        # Change allocation and rebalance.
        Balance(as_timestamp('2024-01-1'), 'B', {
            'VTI': 0.5,
        }).execute(p, quote)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(0, p.position('GOOG'))
        self.assertAlmostEqual(50000.0, p.cash)
        # And back again:
        Balance(as_timestamp('2024-01-1'), 'B', {
            'VTI': 0.5,
            'GOOG': 0.2
        }).execute(p, quote)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(1000, p.position('GOOG'))
        self.assertAlmostEqual(30000.0, p.cash)
        
    def test_rebalance2(self):
        p = Portfolio()
        quote = make_quote({ 'GOOG': 100.0 })
        p.set_quote(quote)
        Balance(as_timestamp('2024-01-1'), 'B', {
            'GOOG': 0.5
        }).execute(p, quote)
        quote = make_quote({ 'GOOG': 200.0 })
        p.set_quote(quote)
        Balance(as_timestamp('2024-01-1'), 'B', {
            'GOOG': 0.5
        }).execute(p, quote)
        self.assertEqual(375, p.position('GOOG'))
        print(p)
        
    def test_value1(self):
        p = Portfolio()
        p.set_quote(make_quote({'GOOG': 100.0}))
        p.buy('GOOG', 10)
        self.assertAlmostEqual(100000, p.value())
        self.assertAlmostEqual(1000, p.holding('GOOG'))
        self.assertAlmostEqual(99000, p.cash)        

    def test_rebalance_default(self):
        p = Portfolio(cash = 10000)
        bounds = 0.2, 0.2
        cash_allocation = 0.2
        vti_allocation = 0.8
        quote = make_quote({ 'VTI': 36.5848 })
        p.set_quote(quote)
        Balance(as_timestamp('2024-01-1'), 'B', {
            'VTI': vti_allocation
        }).execute(p, quote)
        quote = make_quote({ 'VTI': 27.52 })
        p.set_quote(quote)
        Balance(as_timestamp('2024-01-1'), 'B', {
            'VTI': vti_allocation
        }).execute(p, quote)
        # Check the cash holding:
        lo = p.value() * cash_allocation * (1. - bounds[0])
        hi = p.value() * cash_allocation * (1. + bounds[1])
        self.assertTrue(
            lo < p.cash < hi, 
            f"Cash allocation out of bounds {lo:.2f}/{p.cash:.2f}/{hi:.2f}."
        )
        # Check VTI holding:
        holding = p.holding('VTI')
        lo = p.value() * vti_allocation * (1. - bounds[0])
        hi = p.value() * vti_allocation * (1. + bounds[1])
        self.assertTrue(
            lo < holding < hi, 
            f"VTI allocation out of bounds {lo}/{holding}/{hi}."
        )
        print(p)
        
if __name__ == '__main__':
    unittest.main()
