import unittest
from typing import Mapping, Tuple

import pandas as pd

from portfolio import Portfolio
from rules import (
    Balance,
    Buy,
    CashInterest,
    ClosePosition,
    Deposit,
    Dividends,
    Withdraw,
)
from utils import as_timestamp
from yfcache import Quote


def synthetic(cash: float, data: Mapping[str, float]) -> Tuple[Portfolio, Quote]:
    p = Portfolio(cash)
    q = Quote(pd.Timestamp.now(tz='UTC'), {
        (ticker, 'Close'): value for ticker, value in data.items()
    })
    p.set_quote(q)
    return (p, q)
    
def dividends(q: Quote, symbol: str, amount: float) -> Quote:
    q.values[(symbol, 'Dividends')] = amount # type: ignore
    return q

class TestRules(unittest.TestCase):
    start = as_timestamp('2024-01-01')
    
    def test_Buy(self):
        p, q = synthetic(100.0, {'FOO': 10.0})
        Buy(TestRules.start, 'D', 1, 'FOO', 1).execute(p, q)
        self.assertEqual(p.position('FOO'), 1)
        self.assertAlmostEqual(p.cash, 90.0)
        
    def test_ClosePosition(self):
        p, q = synthetic(100.0, {'FOO': 10.0})
        p.set_position('FOO', 2)
        ClosePosition(TestRules.start, 'D', 1, 'FOO').execute(p, q)
        self.assertEqual(p.position('FOO'), 0)
        self.assertAlmostEqual(p.cash, 120.0)
        
    def test_Balance(self):
        p, q = synthetic(100.0, {'FOO': 10.0, 'BAR': 5.0})
        p.set_positions({'FOO': 0, 'BAR': 0})
        Balance(TestRules.start, 'D', { 'FOO': 0.5, 'BAR': 0.5}).execute(p, q)
        self.assertEqual(p.position('FOO'), 5)
        self.assertEqual(p.position('BAR'), 10)
        
    
    def test_Dividends(self):
        p, q = synthetic(100.0, {'FOO': 2})
        p.set_position('FOO', 1)
        Dividends().execute(p, dividends(q, 'FOO', 10.0))
        self.assertAlmostEqual(p.cash, 110.0)
        
    def test_Deposit(self):
        p, q = synthetic(100.0, { 'FOO': 1})
        Deposit(TestRules.start, 'D', 1, 10.0).execute(p, q)
        self.assertAlmostEqual(p.cash, 110.0)
        
    def test_Withdraw(self):
        p, q = synthetic(100.0, { 'FOO': 1})
        Withdraw(TestRules.start, 'D', 1, 10.0).execute(p, q)
        self.assertAlmostEqual(p.cash, 90.0)
        
    def test_cashInterest(self):
        p, q = synthetic(100.0, { 'FOO': 1})
        CashInterest(0.12).execute(p, q)
        self.assertAlmostEqual(p.cash, 101.0)
        
        
        