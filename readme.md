# ledgercalc

A simple multifunction + variables RPN calculator for Ledger (http://www.ledger-cli.org)

Works with Ledger 3 when compiled with the python interface

Must be run via `ledger python ledgercalc.py <journalfile> start_year end_year <commandfile>...`

An example is included, run it with:

    ledger python ledgercalc.py example.lgr 2012 2014 example.commands

## Syntax

Syntax is RPN, so an operation like

    account1 account2 + 
   
adds two accounts, pushes result onto stack.

Accounts containing spaces/regex must be put in double quotes.

Variables are prefixed with `$`, and are assigned like this:

    $taxrate 0.091 = 

Numbers are bare, but amounts less than decimals have to be preceded by a 0 (good: 0.15, bad: .15)

Comments start with `#`


## Output

Output is a list of all variables assigned during each run in `varname = <amount>` format


## Known Bugs

Currently only supports the USD currency.

Account regex parsing isn't the same as ledger, due to the way the python interface works. 

## Change History

2015-12-12: Added exception handling, additional usd/subz commands to force currency conversion, or a zero bounded subtraction, changed order of cli variables to allow multiple command files
