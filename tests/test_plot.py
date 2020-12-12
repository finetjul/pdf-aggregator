import os
from bank_extracts import plot

def test_plotAccounts():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    accounts = plot.readAccounts(os.path.join(dir_path, 'test_plot_1.json'))
    plot.plot_accounts(accounts)
