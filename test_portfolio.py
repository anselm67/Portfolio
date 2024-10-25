import unittest

from portfolio import Portfolio
from yfcache import YFCache

class TestPortfolio(unittest.TestCase):

    def test_default_cash(self):
        p = Portfolio()
        self.assertEqual(p._cash, 100000.0)
        self.assertAlmostEqual(p.value(), 100000.0)

    def test_buy(self):
        p = Portfolio()
        self.assertEqual(p._cash, 100000.0)
        p.buy('vti', 10, 100.0)
        self.assertEqual(p._cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)

    def test_sell_none(self):
        p = Portfolio()
        self.assertRaises(AssertionError, p.sell,'vti', 10, 100.0)

    def test_sell_toomany(self):
        p = Portfolio()
        p.buy('vti', 10, 10.0)
        self.assertRaises(AssertionError, p.sell,'vti', 11, 100.0)

    def test_sell(self):
        p = Portfolio()
        self.assertEqual(p._cash, 100000.0)
        p.buy('vti', 10, 100.0)
        self.assertEqual(p._cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)
        p.sell('vti', 10, 100.0)
        self.assertEqual(p._cash, 100000.0)
        
    def test_set_allocation(self):
        p = Portfolio()
        self.assertAlmostEqual(1.0, p.get_target_allocation(p.CASH_SYMBOL))
        p.set_allocation({
            'VTI': 0.8
        })
        self.assertAlmostEqual(0.2, p.get_target_allocation(Portfolio.CASH_SYMBOL))

    def test_rebalance(self):
        prices = {
            'VTI': 100.0,
            'GOOG': 20.0,
        }
        p = Portfolio()
        p.set_allocation({
            'VTI': 0.5,
            'GOOG': 0.2
        })
        p.balance(prices)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(1000, p.position('GOOG'))
        self.assertAlmostEqual(30000.0, p.cash())
        # Change allocation and rebalance.
        p.set_allocation({
            'VTI': 0.5,
        })
        p.balance(prices)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(0, p.position('GOOG'))
        self.assertAlmostEqual(50000.0, p.cash())
        # And back again:
        p.set_allocation({
            'VTI': 0.5,
            'GOOG': 0.2
        })
        p.balance(prices)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(1000, p.position('GOOG'))
        self.assertAlmostEqual(30000.0, p.cash())
        
    def test_value1(self):
        yfcache = YFCache()
        p = Portfolio(yfcache = yfcache)
        close = yfcache.get_ticker('GOOG').last_price()
        p.buy('GOOG', 10, close)
        self.assertAlmostEqual(100000, p.value())
        
    def test_value2(self):
        yfcache = YFCache()
        p = Portfolio(yfcache = yfcache)
        p.set_position('GOOG', 10)
        close = yfcache.get_ticker('GOOG').last_price()
        self.assertAlmostEqual(10 * close + 100000, p.value())

if __name__ == '__main__':
    unittest.main()
