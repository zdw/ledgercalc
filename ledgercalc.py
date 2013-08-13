#!/usr/bin/env python

import ledger
import sys
import re
import string
import datetime
import copy

if len(sys.argv) != 5:
    print "must be run via `ledger python ledgercalc.py <commandfile> <journalfile> start_year end_year`"
    sys.exit(1)

##### ledger prep #####

# read in the journal file
journal = ledger.read_journal(sys.argv[2])

# create a USD commodity
comms = ledger.commodities
usd = comms.find_or_create('$')

# create dates for start/endpoint
start = datetime.date(int(sys.argv[3]),1,1)
end = datetime.date(int(sys.argv[4]),1,1)

##### ledger functions #####

# find the balance for an account
def balance_acct(acct_name, start_d=None, end_d=None):
    total = ledger.Balance()
    if re.match(r"^[A-Za-z:_\-\ ]*$",acct_name):  # if the account name lacks re's
        account = journal.find_account_re(acct_name)
        return bal_posts_subacct(account, start_d, end_d)
    else:
        return bal_re_acct(acct_name,start_d,end_d)

# recursively accumulate the balance for all posts/subaccounts of given account
def bal_posts_subacct(account, start_d=None, end_d=None):
    total = ledger.Balance()
    if account == None: # if nothing was matched, return empty balance object
        return total
    for post in account.posts():
        if start_d and post.date < start_d:
            continue
        if end_d and post.date > end_d:
            continue
        total += post.amount
    for subacct in account.accounts():
        total += bal_posts_subacct(subacct, start_d, end_d)
    return total

# determine balance of account path that contains re's
def bal_re_acct(acct_name,start_d=None, end_d=None):
    acct_list = string.split(acct_name,':')
    top_acct_name = acct_list[0]
    if top_acct_name == ".*":
        top_acct = journal.find_account_re('')
    else:
        acct_list.pop(0)
        top_acct = journal.find_account_re(top_acct_name)

    return bal_re_subacct_list(top_acct,acct_list,start_d,end_d)

# recursively determine balance for matching subaccounts with re's
def bal_re_subacct_list(top_acct, acct_list, start_d=None, end_d=None):
    total = ledger.Balance()

    if len(acct_list) == 0 :  # if we've matched to end of acct_list, get balance
        total += bal_posts_subacct(top_acct,start_d,end_d)
    else:
        sub_acct_name = acct_list.pop(0)
        for subacct in top_acct.accounts():
            if re.search(sub_acct_name, subacct.name):
                rec_acct_list = copy.copy(acct_list) # as acct_list will be changed in recursion
                total += bal_re_subacct_list(subacct,rec_acct_list,start_d,end_d)
    return total

# create a lexical scanner
# notes: http://www.evanfosmark.com/2009/02/sexy-lexing-with-python/
# also: http://pythonfiddle.com/markdown-calculator-test/
# also?: https://gist.github.com/thepaul/1309885
#
# syntax is RPN, so "account1 account2 +" adds two accounts, pushes onto stack
# accounts containing spaces/regex must be put in double quotes
# variables are prefixed with $
# Numbers are bare, but decimals have to be preceded by a 0 (good: 0.15, bad: .15)
# comments start with #
#

##### scanner functions #####

# tokens that hold balances are tuples of (TYPE, <balance object>, re matched text)

def account(scanner, token):
    token_noq = re.sub(r'\"',r'',token)  # remote quotes from token
    bal = balance_acct(token_noq,start,end)
    return "ACCT", bal, token_noq

def variable(scanner, token):
    return "VAR", None, token

def number(scanner, token):
    num = ledger.Balance()
    num += "$ %s" % token
    return "NUM", num, token

# simpler tokens are just (TYPE, re matched text)

def assign(scanner, token):
    return "ASSIGN", token

def operator(scanner, token):
    return "OPERATOR", token

def singleop(scanner, token):
    return "SINGLEOP", token

def comment(scanner, token):
    return "COMMENT", token

def endofline(scanner, token):
    return "EOL", token

# The scanner re list
scanner = re.Scanner([
    (r"max|min", operator), # max and min are operators
    (r"abs|neg", singleop), # abs and neg take only operate on a single value
    (r"[A-Za-z][\w:]*", account),  # bare, simple, no wildcard accounts
    (r"\"[A-Za-z\.][\w\s_:\-\.\*]*\"", account), # accounts can have spaces/re when in quotes
    (r"\$\w+", variable), # variables start with $
    (r"\+|\-|\*|\\", operator), 
    (r"\=", assign),
    (r"[0-9]+(\.[0-9]+)?", number),
    (r"\n+", endofline),   # newlines = end of statement
    (r"#.*", comment), # comments start with hashes
    (r"\s+", None), # whitespace
    ])

# housekeeping vars
linenum = 0;

# stores variable state
var_dict = {}

# to strip the $ off of variables
re_devar = re.compile("\$(\w+)")

# read in the commands file line by line
with open(sys.argv[1],'r') as f:
    for line in f:
        linenum += 1

        # parse it
        tokens, remainder = scanner.scan(line)
        if remainder:
            print "line #%s, invalid commands, scanner remainder: %s" % (linenum, remainder)
            sys.exit(1)

        # print tokens # dumps the entire parsed scanner output, great for debugging

        cursor = 0
        while cursor < len(tokens):
            tokentype = tokens[cursor][0]

            if tokentype == "OPERATOR":
                func = tokens.pop(cursor)
                if cursor < 2:
                    print "tried to perform a: %s without enough operands" % (func[1])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                op1 = tokens.pop(cursor-1)
                if (op1[0] != "ACCT" and op1[0] != "VAR" and op1[0] != "NUM"):
                    print "invalid operation: %s on a %s" % (func[1], op1[0])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                if (op1[0] == "VAR" and op1[1] == None):
                    print "variable: %s referenced, but has not been set" % (op1[2])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                op2 = tokens.pop(cursor-2)
                if (op2[0] != "ACCT" and op2[0] != "VAR" and op2[0] != "NUM"):
                    print "invalid operation: %s on a %s" % (func[1], op2[0])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                if (op2[0] == "VAR" and op2[1] == None):
                    print "variable: %s referenced, but has not been set" % (op2[2])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                if func[1] == "+":
                    calc = op2[1] + op1[1]
                elif func[1] == "-":
                    calc = op2[1] - op1[1]
                # Balance objects can't be mul/div'ed with each other, so conv to amounts
                elif func[1] == "*":
                    calc = op2[1] * op1[1].to_amount()
                elif func[1] == "/":
                    calc = op2[1] / op1[1].to_amount()
                elif func[1] == "max":
                    if op1[1] > op2[1]:
                        calc = op1[1]
                    else:
                        calc = op2[1]
                elif func[1] == "min":
                    if op1[1] < op2[1]:
                        calc = op1[1]
                    else:
                        calc = op2[1]
                else:
                    print "Undefined, but matched, operator: %s" % func[1]
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                tokens.insert(cursor-2,["NUM", calc, calc.to_string()])
                cursor -= 2 # compensate for 2 popped items

            elif tokentype == "SINGLEOP":
                func = tokens.pop(cursor)
                if cursor < 1:
                    print "tried to perform a: %s without enough operands" % (func[1])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                op1 = tokens.pop(cursor-1)
                if (op1[0] != "ACCT" and op1[0] != "VAR" and op1[0] != "NUM"):
                    print "invalid operation: %s on a %s" % (func[1], op1[0])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                if (op1[0] == "VAR" and op1[1] == None):
                    print "variable: %s referenced, but has not been set" % (op1[2])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                if func[1] == "abs":
                    calc = abs(op1[1])
                elif func[1] == "neg":
                    calc = - op1[1]
                tokens.insert(cursor-1,["NUM", calc, calc.to_string()])
                cursor -= 1 #compensate for a single popped item


            elif tokentype == "ASSIGN":
                func = tokens.pop(cursor)
                if cursor < 2:
                    print "tried to perform a: %s without enough operands" % (func[1])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                op1 = tokens.pop(cursor-1)
                if (op1[0] != "ACCT" and op1[0] != "VAR" and op1[0] != "NUM"):
                    print "invalid operation: %s on a %s" % (func[1], op1[0])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                if (op1[0] == "VAR" and op1[1] == None):
                    print "variable: %s referenced, but has not been set" % (op1[2])
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)
                op2 = tokens.pop(cursor-2)
                if op2[0] == "VAR":
                    value = op1[1]
                    tokens.insert(cursor-2,["VAR",value,op2[2]])
                    vartxt = re.match(re_devar,op2[2]).group(1)
                    var_dict[vartxt] = value # store value for printing/assignment
                    cursor -= 2 # compensate for 2 popped items
                else:
                    print "tried to assign to non-variable!"
                    print "line: %s, cursor: %s, length: %s" % (linenum, cursor, len(tokens))
                    sys.exit(1)

            elif tokentype == "VAR":
                var = tokens.pop(cursor)
                value = None # default value is none
                vartxt = re.match(re_devar,var[2]).group(1)
                if vartxt in var_dict: # if variable has been stored earlier, assign it
                    value = var_dict[vartxt]
                tokens.insert(cursor,["VAR",value,var[2]])

            #increment cursor
            cursor += 1

# print out sorted list of variables
for key in sorted(var_dict.keys()):
    print "%s = %s" % (key, var_dict[key].value(usd))




