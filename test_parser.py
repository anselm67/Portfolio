import unittest
from parser import (
    Schedule,
    SyntaxError,
    parse_dollars,
    parse_percent,
    parse_schedule,
    parse_string,
    trim_line,
)
from typing import cast

from actions import (
    Balance,
    Buy,
    CashInterest,
    ClosePosition,
    Deposit,
    Dividends,
    Withdraw,
)
from utils import as_timestamp
from yfcache import YFCache


class TestParser(unittest.TestCase):

    def test_parse_percent(self):
        self.assertEqual(0.05, parse_percent('5%'))
        self.assertEqual(1.0, parse_percent('100%'))
        self.assertEqual(0.5, parse_percent('0.5'))
        self.assertRaises(SyntaxError, parse_percent, '1.2')
        
    def test_trim_line(self):
        self.assertEqual('10', trim_line('10  # comments '))
    
    def test_parse_dollars(self):
        self.assertAlmostEqual(parse_dollars('$10'), 10.0)
        self.assertAlmostEqual(parse_dollars('$-10.2543'), -10.2543)
        self.assertAlmostEqual(parse_dollars('$10k'), 10000.0)
        self.assertAlmostEqual(parse_dollars('$10.2k'), 10200.0)
        self.assertAlmostEqual(parse_dollars('$10m'), 10000000.0)

        self.assertRaises(SyntaxError, parse_dollars, '10')
        self.assertRaises(SyntaxError, parse_dollars, '$10x')
        
    def test_parse_dollars_2(self):
        self.assertAlmostEqual(parse_dollars('  $100 '), 100.0)

    def test_parse_schedule(self):
        schedule, line = parse_schedule('2020-01-01 deposit')
        self.assertEqual(line, 'deposit')
        self.assertIsNotNone(schedule)
        schedule = cast(Schedule, schedule)
        self.assertEqual(schedule.start_date, as_timestamp('2020-01-01'))
        self.assertEqual(schedule.freq, 'D')
        
    def test_parse_schedule_freq(self):
        schedule, line = parse_schedule('2020-01-01[W-MON] deposit $100k')
        self.assertEqual(line, 'deposit $100k')
        self.assertIsNotNone(schedule)
        schedule = cast(Schedule, schedule)
        self.assertEqual(schedule.start_date, as_timestamp('2020-01-01'))
        self.assertEqual(schedule.freq, 'W-MON')

    def test_parse_schedule_count_1(self):
        schedule, line = parse_schedule('2020-01-01[1xW-MON] deposit $100k')
        self.assertEqual(line, 'deposit $100k')
        self.assertIsNotNone(schedule)
        schedule = cast(Schedule, schedule)
        self.assertEqual(schedule.start_date, as_timestamp('2020-01-01'))
        self.assertEqual(schedule.freq, 'W-MON')
        self.assertEqual(schedule.count, 1)
        
    def test_parse_schedule_count_2(self):
        schedule, line = parse_schedule('2020-01-01 [  1x  W-MON ] deposit $100k')
        self.assertEqual(line, 'deposit $100k')
        self.assertIsNotNone(schedule)
        schedule = cast(Schedule, schedule)
        self.assertEqual(schedule.start_date, as_timestamp('2020-01-01'))
        self.assertEqual(schedule.freq, 'W-MON')
        self.assertEqual(schedule.count, 1)

    def test_parse_Dividends(self):
        actions = parse_string("dividends")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Dividends))
        
    def test_parse_CashInterest(self):
        actions = parse_string("cash-interest  5%")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], CashInterest))
        self.assertAlmostEqual(cast(CashInterest, actions[0]).monthly_rate, 0.05 / 12)
    
    def test_parse_Deposit(self):
        actions = parse_string("2020-01-01 deposit $10k")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Deposit))
        a = cast(Deposit, actions[0])
        self.assertEqual(a.count, 1)
        self.assertEqual(a.amount, 10000)
        self.assertEqual(a.start, as_timestamp('2020-01-01'))
            
    def test_parse_Deposit_schedule(self):
        actions = parse_string("2020-01-01 [12xBMS] deposit $10k")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Deposit))
        a = cast(Deposit, actions[0])
        self.assertAlmostEqual(a.amount, 10000 / 12)
        self.assertEqual(a.start, as_timestamp('2020-01-01'))
        self.assertEqual(a.freq, 'BMS')
        self.assertEqual(a.count, 12)
        
    def test_parse_Balance(self):
        actions = parse_string("balance GOOG: 10%, VTI: 40%, QQQ: 20%")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Balance))
        a = cast(Balance, actions[0])
        self.assertEqual(a.start, YFCache.START_DATE)
        self.assertAlmostEqual(a.alloc['GOOG'], 0.1)
        self.assertAlmostEqual(a.alloc['VTI'], 0.4)
        self.assertAlmostEqual(a.alloc['QQQ'], 0.2)
        self.assertAlmostEqual(a.cash_alloc, 0.3)
        
    def test_parse_Withraw(self):
        actions = parse_string("2020-01-01 [52 x W-MON] withdraw $1k")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Withdraw))
        a = cast(Withdraw, actions[0])
        self.assertEqual(a.start, as_timestamp('2020-01-01'))
        self.assertAlmostEqual(a.amount, 1000 / 52)
        
    def test_parse_Buy(self):
        actions = parse_string("2020-01-01 [12 x W-MON] buy 120 AAPL ")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Buy))
        a = cast(Buy, actions[0])
        self.assertEqual(a.start, as_timestamp('2020-01-01'))
        self.assertEqual(a.symbol, 'AAPL')
        self.assertAlmostEqual(a.quantity, 120 / 12)
        
    def test_parse_ClosePosition(self):
        actions = parse_string("2022-01-01 [ 52 x W-MON ] close-position AAPL # Comments there")
        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], ClosePosition))
        a = cast(ClosePosition, actions[0])
        self.assertEqual(a.start, as_timestamp('2022-01-01'))
        self.assertEqual(a.symbol, 'AAPL')
