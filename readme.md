A simple 4-function + variables RPN calculator for Ledger (http://www.ledger-cli.org)

Works with Ledger 3 when compiled with the python interface

Must be run via `ledger python ledgercalc.py <commandfile> <journalfile> start_year end_year`

Syntax is RPN, so 

   account1 account2 + 
   
adds two accounts, pushes result onto stack.

Accounts containing spaces/regex must be put in double quotes.

Variables are prefixed with $, and are assigned like this:

    $taxrate 0.091 = 

Numbers are bare, but amounts less than decimals have to be preceded by a 0 (good: 0.15, bad: .15)

Comments start with #

Currently only supports the USD currency. 


