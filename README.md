# Portfolio simulation tool.

This tool takes as input two things:
- A portfolio as in a stock allocation and soem cash amount, described in a json file,
- A "program" or instructions on how to handle the portfolio,
it then simulates the action of the instructions on the portoflio through a given date
range and outputs a yearly percentage gain.

As an example, consider the following program in sample/retires.rules

\# Enable dividends tracking monthly.
dividends

\# Every month, deposit $100
2000-01-01 [BMS] deposit $100

balance VTI: 100%

This simulates a portfolio, with dividend tracking, in which $100 is deposited every 
month and stock allocation consists in 100% VTI - basically buying as much VTI as posseble 
through time. To simulate this we run:

\# ./psym.py --from 2000-01-01 -p '*empty*' samples/retire.rules --plot
Empty Portfolio $213,654.23
        Cash: $128.90/0.06%
        VTI     $213,525.33/742/99.94%
Annual returns: 35.81%

You can manage the cachefrom psym.py, check the help with 
\# ./psym.py --help

Here is a list of files in this directory, and their purpose:

- psym.py
    Is the portfolio simulator
- parser.py
    Parser for the portfolio simulator .rules file.
- rules.py
    Implements the rules supported by the portfolio simulator, 
    this is the place to go to add new rules constructs.
- yfcache.py
    A very rudmentary yfinance cache, that just gets the job done.
- test_*py
    Various unit tests.
- samples/
    Has various sample portfolio and rule files.

The following files are historical, no longer used.
    
- entry.py
    Superseeded by psym.py, simulates market entry strategies.
- rebalance.py
    Superseeded by psym.py, simulates rebalancing strategies.
- stock.py
    Hands on yfinance and pyplot example.
