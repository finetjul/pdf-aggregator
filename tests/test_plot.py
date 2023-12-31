import datetime
import os
from matplotlib import get_backend

from sortedcontainers import SortedDict
#from bank_extracts import plot
from aggregator import plot

def test_get_balance():
    a = SortedDict()

    d1 = datetime.date(2019, 12, 4)
    d2 = datetime.date(2021, 6, 4)
    d3 = datetime.date(2022, 1, 4)
    d4 = datetime.date(2022, 6, 4)
    d5 = datetime.date(2023, 1, 4)

    a[d1] = 10
    a[d2] = 20
    a[d3] = 30
    a[d4] = 50

    plot.get_balance(a, d1)
    plot.get_balance(a, d1)
    plot.get_balance(a, d1)
    plot.get_balance(a, d1)

    plot.get_balance(a, d2)
    plot.get_balance(a, d2)
    plot.get_balance(a, d2)
    
    plot.get_balance(a, d3)
    plot.get_balance(a, d3)
    plot.get_balance(a, d3)
    
    plot.get_balance(a, d4)
    plot.get_balance(a, d4)
    plot.get_balance(a, d4)

    plot.get_balance(a, d5)
    plot.get_balance(a, d4)
    plot.get_balance(a, d5)
    plot.get_balance(a, d1)


def test_plotAccounts():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_json_path = os.path.join(dir_path, 'data', 'test_plot_1.json')
    accounts = plot.readAccounts(test_json_path)
    plot.plot_accounts(accounts)

def test_plotAccountsYearly():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_json_path = os.path.join(dir_path, 'data', 'test_plot_1.json')
    accounts = plot.readAccounts(test_json_path)
    plot.plot_accounts(accounts, yearly=True)
