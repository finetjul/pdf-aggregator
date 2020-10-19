import collections
import datetime
import dateutil.parser
import json
import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import mplcursors
import numpy
import pathlib
# Use SortedDict (instead of OrderedDict) to bisect
from sortedcontainers import SortedDict

def fromJSON(accounts_file):
    def replace_keys(accounts):
        new_accounts = { }
        for key in accounts.keys():
            date = None
            try:
                date = dateutil.parser.parse(key)
            except Exception:
                pass
            if isinstance(date, datetime.date):
                new_accounts[date] = accounts[key]
            elif isinstance(accounts[key], dict):
                new_accounts[key] = replace_keys(accounts[key])
            else:
                new_accounts[key] = accounts[key]
        return new_accounts


    accountsJSON = json.load(accounts_file)
    accounts = replace_keys(accountsJSON)
    return accounts


def readAccounts(accounts_path):
    with open(accounts_path, encoding='utf-8') as accounts_file:
        accounts = fromJSON(accounts_file)
    return accounts

account_types = ['checking', 'saving', 'life-insurance', 'loan', 'real-estate']

def plotAccounts(accounts, ignored_categories=[], log_scale=False, stacked=False):
    # Stack do not work with loans:
    if stacked:
        ignored_categories.append('loan')
    # Group accounts per account type
    grouped_accounts = collections.OrderedDict()
    for account_type in [*account_types, 'other']:
        if account_type in ignored_categories:
            print(account_type, 'is ignored')
            continue

        for account_id in accounts.keys():
            act = accounts[account_id].get('account', {}).get('account-type')
            print(account_id, act)
            if act == account_type or (account_type == 'other' and
               act not in account_types and act not in ignored_categories):
                grouped_accounts.setdefault(account_type, {})[account_id] = accounts[account_id]

    plots = []
    labels = []
    # {
    #   'checking': {
    #      'BNP-foo': {
    #         '2020-01-01': 10,
    #         '2020-02-01': 20,
    #      }
    #   }
    # }
    grouped_balances = collections.OrderedDict()
    type_index = 0
    sorted_dates = SortedDict()
    for account_type in grouped_accounts.keys():
        account_index = 0
        for account_id in grouped_accounts[account_type]:
            balances = accounts[account_id].get('balances', {})

            share = accounts[account_id].get('account', {}).get('share', 1)
            sorted_balances = SortedDict((date, value * share) for date, value in balances.items())
            grouped_balances.setdefault(account_type, {})[account_id] = sorted_balances
            sorted_dates.update(dict.fromkeys(sorted_balances.keys(), 0))

            x, y = zip(*sorted_balances.items())

            if not stacked:
                color_index = type_index
                if len(grouped_accounts[account_type]) > 1:
                    color_index += 0.5 * account_index / (len(grouped_accounts[account_type])-1)

                if len(grouped_accounts) > 1:
                    color_index /= len(grouped_accounts) - 1
                c = cm.rainbow(color_index)

                plots += plt.plot(x, y, color=c, label=account_id)
            labels += [account_id]
            account_index += 1
        type_index += 1

    # Total
    for day in sorted_dates:
        all = []
        for accounts in grouped_balances.values():
            for balances in accounts.values():
                # 0 if day is before first account entry
                if balances.keys()[0] <= day:
                    index = balances.bisect(day)
                    # last value if day is after last account entry
                    index -= 1
                    key = balances.iloc[index]
                    all.append(balances[key])
                else:
                    all.append(0)
        sorted_dates[day] = all if stacked else sum(all)
    if stacked:
        fig, ax = plt.subplots()
        number_of_accounts = len(next(iter(sorted_dates.values())))
        colors = cm.rainbow(numpy.linspace(0, 1, number_of_accounts))
        values = list(map(list, zip(*sorted_dates.values())))
        ax.stackplot(sorted_dates.keys(),
                    list(map(list, zip(*sorted_dates.values()))),
                    labels=labels,
                    colors=colors)
    else:
        # Total
        x, y = zip(*sorted_dates.items())
        plots += plt.plot(x, y, color='black', label='Total')
        labels += ['Total']
        grouped_balances['total'] = sorted_dates

    if stacked:
        ax.legend(loc='upper left')
    else:
        plt.legend(plots, labels)

    if log_scale:
        plt.yscale('symlog')
        plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        plt.gca().yaxis.get_major_formatter().set_scientific(False)

    if not stacked:
        mplcursors.cursor().connect(
            "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        # format the coords message box
        plt.gca().format_xdata = mdates.DateFormatter('%Y-%m-%d')
        plt.gca().format_ydata = lambda x: '%1.2f' % x  # format the price.

        plt.gca().grid(True)

    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file_or_folder",
                        help="a json file or a folder containing json files")
    parser.add_argument("--ignore", nargs="+", default=[],
                        help="Account type to ignore (e.g. -i loan -i real-estate")
    parser.add_argument("--log", action="store_true",
                        help="Use log scale")
    parser.add_argument("--stack", action="store_true",
                        help="Stack accounts")

    args = parser.parse_args()

    if pathlib.Path(args.file_or_folder).is_file():
        accounts = readAccounts(args.file_or_folder)
    else:
        accounts = {}
        for root, dirs, files in os.walk(args.file_or_folder):
            for file in files:
                accounts_file_path = os.path.join(root, file)
                [stem, ext] = os.path.splitext(accounts_file_path)
                if ext == '.json':
                    accounts.update(readAccounts(accounts_file_path))

    plotAccounts(accounts, ignored_categories=args.ignore, log_scale=args.log, stacked=args.stack)
