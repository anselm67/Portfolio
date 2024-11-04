import unittest

from portfolio import Portfolio


class TestPortfolio(unittest.TestCase):

    def test_default_cash(self):
        p = Portfolio()
        self.assertEqual(p.cash, 100000.0)
        self.assertAlmostEqual(p.value(), 100000.0)

    def test_buy(self):
        p = Portfolio()
        self.assertEqual(p.cash, 100000.0)
        p.set_prices({ 'vti': 100.0 })
        p.buy('vti', 10)
        self.assertEqual(p.cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)

    def test_sell_none(self):
        p = Portfolio()
        p.set_prices({ 'vti': 100.0 })
        self.assertRaises(AssertionError, p.sell, 'vti', 10)

    def test_sell_toomany(self):
        p = Portfolio()
        p.set_prices({ 'vti': 100.0 })
        p.buy('vti', 10)
        self.assertRaises(AssertionError, p.sell,'vti', 11)

    def test_sell(self):
        p = Portfolio()
        p.set_prices({ 'vti': 100.0 })
        self.assertEqual(p.cash, 100000.0)
        p.buy('vti', 10)
        self.assertEqual(p.cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)
        p.sell('vti', 10)
        self.assertEqual(p.cash, 100000.0)
        
    def test_set_allocation(self):
        p = Portfolio()
        self.assertAlmostEqual(1.0, p.get_cash_allocation())
        p.set_allocation({
            'VTI': 0.8
        })
        self.assertAlmostEqual(0.2, p.get_cash_allocation())

    def test_rebalance1(self):
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
        self.assertAlmostEqual(30000.0, p.cash)
        # Change allocation and rebalance.
        p.set_allocation({
            'VTI': 0.5,
        })
        p.balance(prices)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(0, p.position('GOOG'))
        self.assertAlmostEqual(50000.0, p.cash)
        # And back again:
        p.set_allocation({
            'VTI': 0.5,
            'GOOG': 0.2
        })
        p.balance(prices)
        self.assertEqual(500, p.position('VTI'))
        self.assertEqual(1000, p.position('GOOG'))
        self.assertAlmostEqual(30000.0, p.cash)
        
    def test_rebalance2(self):
        p = Portfolio()
        p.set_allocation({ 'GOOG': 0.5 })
        p.balance({ 'GOOG': 100.0 })
        p.balance({ 'GOOG': 200.0 })
        self.assertEqual(375, p.position('GOOG'))
        print(p)
        
    def test_value1(self):
        p = Portfolio()
        p.set_prices({'GOOG': 100.0})
        p.buy('GOOG', 10)
        self.assertAlmostEqual(100000, p.value())
        self.assertAlmostEqual(1000, p.get_holding('GOOG'))
        self.assertAlmostEqual(99000, p.cash)        

    def test_rebalance_default(self):
        p = Portfolio(cash = 10000)
        bounds = 0.2, 0.2
        p.set_allocation({ 'VTI': 0.8 })
        for op in p.balance({ 'VTI': 36.5848 }, bounds):
            print(op)
        print(p)
        for op in p.balance({ 'VTI': 27.52 }):
            print(op)
        # Check the cash holding:
        lo = p.value() * p.get_cash_allocation() * (1. - bounds[0])
        hi = p.value() * p.get_cash_allocation() * (1. + bounds[1])
        self.assertTrue(
            lo < p.cash < hi, 
            f"Cash allocation out of bounds {lo:.2f}/{p.cash:.2f}/{hi:.2f}."
        )
        # Check VTI holding:
        holding = p.get_holding('VTI')
        lo = p.value() * p.get_target_allocation('VTI') * (1. - bounds[0])
        hi = p.value() * p.get_target_allocation('VTI') * (1. + bounds[1])
        self.assertTrue(
            lo < holding < hi, 
            f"VTI allocation out of bounds {lo}/{holding}/{hi}."
        )
        print(p)
        
if __name__ == '__main__':
    unittest.main()
