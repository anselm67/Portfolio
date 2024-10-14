import unittest

from portfolio import Portfolio

class TestPortfolio(unittest.TestCase):

    def test_default_cash(self):
        p = Portfolio()
        self.assertEqual(p.cash, 100000.0)

    def test_buy(self):
        p = Portfolio()
        self.assertEqual(p.cash, 100000.0)
        p.buy('vti', 10, 100.0)
        self.assertEqual(p.cash, 99000.0)
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
        self.assertEqual(p.cash, 100000.0)
        p.buy('vti', 10, 100.0)
        self.assertEqual(p.cash, 99000.0)
        self.assertEqual(p.position('vti'), 10)
        p.sell('vti', 10, 100.0)
        self.assertEqual(p.cash, 100000.0)

        

if __name__ == '__main__':
    unittest.main()
