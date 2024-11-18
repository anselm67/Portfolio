#!/usr/bin/env python3

import re
import sys
from dataclasses import dataclass
from io import StringIO
from typing import IO, Callable, List, Mapping, Optional, Tuple

import pandas as pd

from rules import (
    Balance,
    Buy,
    CashInterest,
    ClosePosition,
    Deposit,
    Dividends,
    Rule,
    Withdraw,
)
from utils import as_timestamp
from yfcache import YFCache

BLANK_LINE = re.compile(r'^\s*(#.*)?$')

class SyntaxError(Exception):
    
    filename: str
    lineno: int
    
    def __init__(self, message: str):
        super().__init__(message)

    def decorate(self, filename: str, lineno: int):
        self.filename = filename
        self.lineno = lineno

@dataclass 
class Schedule:    
    start_date: pd.Timestamp
    freq: Optional[ str ] = None
    count: int = -1
            
# Parses percent as either xx.xx% or a float between 0 and 1
PERCENT = re.compile(r'\s*(\d+(\.\d+)?)%\s*')
def parse_percent(text: str) -> float:
    if (m := re.match(PERCENT, text)) is not None:
        value = float(m.group(1)) / 100.0
    else:
        try:
            value = float(text)
        except ValueError:
            raise SyntaxError(f"Invalid percentage '{text}'")
    if 0 <= value <= 1.0:
        return value
    raise SyntaxError(f"Percentage {value} should be between 0 and 1.")
    
# Removes any trailing spaces and comments from given text.    
TRIM_LINE=re.compile(r'^(.*?)(\s*#.*)?$')
def trim_line(text: Optional[ str ]) -> str:
    if text is None:
        return ''
    if (m := re.match(TRIM_LINE, text)) is not None:
        return m.group(1)
    else:
        return text

# Parses a dollar amount as $<number>(unit)
DOLLAR_AMOUNT=re.compile(r'^\s*\$(-?\d+(?:\.\d+)?)(m|k)?\s*$')
def parse_dollars(text: str) -> float:
    if (m := re.match(DOLLAR_AMOUNT, text)) is not None:
        units = m.group(2)
        if units == None or units == '':
            return float(m.group(1))
        elif units == 'k':
            return 1000 * float(m.group(1))
        elif units == 'm':
            return 1000000 * float(m.group(1))
        else:
            raise SyntaxError(f"Invalid units in {text}, expected m, k or none.")
    else:
        raise SyntaxError(f"Invalid $ amount {text}")

DATE_REGEXP = re.compile(r'^(\d{4}-\d{2}-\d{2})\s+(.*)$')

SCHEDULE=re.compile(r'^(\d{4}-\d{2}-\d{2})\s*(?:\[\s*(?:(\d+)\s*x)?\s*(\S+)\s*\])?\s*(.*)$')
def parse_schedule(line: str) -> Tuple [Optional[Schedule], Optional[str]]:
    if (m := re.match(SCHEDULE, line)) is not None:
        start = as_timestamp(m.group(1))
        freq = m.group(3) or 'D'
        count = int(m.group(2)) if m.group(2) else -1
        return Schedule(start, freq, count), m.group(4)
    else:
        return None, None
    
def parse_Dividends(line: str, schedule: Optional[Schedule] = None) -> Dividends:
    if re.match(BLANK_LINE, line):
        return Dividends()
    raise SyntaxError(f"Unexpected symbols f{line}")

def parse_CashInterest(line: str, schedule: Optional[Schedule] = None) -> CashInterest:
    return CashInterest(parse_percent(line))
    
def parse_Deposit(line: str, schedule: Optional[Schedule] = None) -> Deposit:
    amount = parse_dollars(line)
    assert schedule is not None, "Deposit requires a start date."
    return Deposit(schedule.start_date, 
                   schedule.freq or 'B', 
                   1 if schedule.count < 0 else schedule.count, 
                   amount)

TARGET=re.compile(r'^\s*([^:\s]+)\s*:\s*(\d+(?:\.\d*)?%?)\s*$')
def parse_Balance(line: str, schedule: Optional[Schedule] = None) -> Balance:
    if schedule is None:
        schedule = Schedule(YFCache.START_DATE, 'B', -1)
    # Parse the requested allocation:
    alloc: Mapping[str, float] = { }
    for target in line.split(','):
        if (m := re.match(TARGET, target)) is not None:
            alloc[m.group(1)] = parse_percent(m.group(2))
        else:
            raise SyntaxError(f"Invalid target {target}")
    if sum(alloc.values()) > 1.0:
        raise SyntaxError(f"Allocation exceeds 100%")
    return Balance(schedule.start_date, schedule.freq or 'B', alloc)
    
def parse_Withdraw(line: str, schedule: Optional[Schedule] = None) -> Withdraw:
    amount = parse_dollars(line)
    assert schedule is not None, "Withdraw requires a start date."
    return Withdraw(schedule.start_date, schedule.freq or 'D', schedule.count, amount)
    
BUY = re.compile(r'^\s*(\d+)\s+(\S+)\s*$')
def parse_Buy(line: str, schedule: Optional[Schedule] = None) -> Buy:
    if schedule is None:
        schedule = Schedule(YFCache.START_DATE, 'B', 1)
    if (m := re.match(BUY, line)) is None:
        raise SyntaxError(f"Invalid buy parameters {line}, expecting QUANTITY TICKER.")
    return Buy(schedule.start_date, 
               schedule.freq or 'B', 
               1 if schedule.count < 0 else schedule.count, 
               m.group(2), int(m.group(1)))

TICKER=re.compile(r'^\s*([\S]+)\s*$')
def parse_ClosePosition(line: str, schedule: Optional[Schedule] = None) -> ClosePosition:
    if (m := re.match(TICKER, line)) is None:
        raise SyntaxError(f"Which TICKER do you want to close the position of.")
    if schedule is None:
        raise SyntaxError("ClosePosition requires a start date.")
    return ClosePosition(schedule.start_date, 
                         schedule.freq or 'B', 
                         1 if schedule.count < 0 else schedule.count, 
                         m.group(1))
    
PARSERS: Mapping[str, Callable[[str, Optional[Schedule]], Rule]] = {
    'dividends': parse_Dividends,
    'cash-interest': parse_CashInterest,
    'deposit': parse_Deposit,
    'balance': parse_Balance,
    'withdraw': parse_Withdraw,
    'buy': parse_Buy,
    'close-position': parse_ClosePosition
}

FIRST_TOKEN = re.compile(r'^(\S+)(\s.*)?$')
def parse_rule(text:str, schedule: Optional[ Schedule ] = None) -> Rule:
    if (m := re.match(FIRST_TOKEN, text)) is not None:
        if (parser := PARSERS.get(m.group(1))) is not None:
            return parser(trim_line(m.group(2)), schedule)
        else:
            raise SyntaxError(f"Unknown rule '{m.group(1)}'")
    raise SyntaxError(f"Invalid rule {text}")

def parse_file(filename: str, file: IO[str]) -> List [ Rule ]:
    actions : List[ Rule ]= [] 
    lineno = 0
    for line in file:
        try:
            lineno += 1
            if re.match(BLANK_LINE, line):
                continue
            schedule, text = parse_schedule(line)
            if schedule is not None:
                if text is None or text == '':
                    raise SyntaxError(f"No rules defined for schedule in {line}.")
                actions.append(parse_rule(text, schedule))
            else:
                actions.append(parse_rule(line))
        except SyntaxError as e:
            e.decorate(filename, lineno) 
            raise e
            
    return actions

def parse_string(text: str) -> List[ Rule ]:
    return parse_file('string', StringIO(text))

def parse(filename: str) -> List[ Rule ]:
    with open(filename, 'r') as file:
        return parse_file(filename, file)
            
    
if __name__ == '__main__':
    for arg in sys.argv[1:]:
        try:
            rules = parse(arg)
            print(f"{arg} ok: {len(rules)} actions.")
        except SyntaxError as e:
            print(f"Error {arg} at line {e.lineno}: {e}")