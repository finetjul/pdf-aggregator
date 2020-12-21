import calendar
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
from scipy import interpolate


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
    """
    @return a dictionary where keys are account names
    """
    with open(accounts_path, encoding='utf-8') as accounts_file:
        accounts = fromJSON(accounts_file)
    return accounts

all_account_types={
    'checking': {
        'account': {
            'color': 'royalblue'
        }
    }, 'saving': {
        'account': {
            'color': 'tomato'
        }
    }, 'life-insurance': {
        'account': {
            'color': 'olivedrab'
        }
    }, 'loan': {
        'account': {
            'color': 'gold'
        }
    }, 'real-estate': {
        'account': {
            'color': 'sandybrown'
        }
    },
        'crowd-funding': {
         'account': {
            'color': 'green'
        }
    }, 'other': {
        'account': {
            'color': 'silver'
        }
    }
}

def get_account_properties(accounts, account_id):
    """ Return the account-type property of an account referenced by its id
    Supports account redirection.
    """
    account = accounts.get(account_id, {}).get('account', None)
    if not isinstance(account, dict):
        account = accounts.get(account, {})
    if account:
        default_account = all_account_types.get(account.get('account-type'),{}).get('account', {})
        account = {**default_account, **account}
    return account

def toTimestamp(day):
    return calendar.timegm(day.timetuple())

def toTimestamps(days):
    return [toTimestamp(d) for d in days]

def get_balance(sorted_balances, day):
    """
    Return the balance for a given day. Existing or not.
    Balance is Hermite interpolated.
    """
    days = toTimestamps(sorted_balances.keys())

    # 1: Hermite interpolation:
    if len(days) > 3 and toTimestamp(day) >= days[0] and toTimestamp(day) <= days[-1]:
        f = interpolate.PchipInterpolator(days, sorted_balances.values())
        return f(toTimestamp(day))

    # 2: linear interpolation:
    return numpy.interp(toTimestamp(day), days, sorted_balances.values(), 0)

    # if sorted_balances.keys()[0] > day:
    #     return 0
    # index = sorted_balances.bisect(day)
    # # last value if day is after last account entry
    # index -= 1
    # key = sorted_balances.iloc[index]
    # return sorted_balances[key]

def get_account_balance(accounts, account_id, day, *args, **kwargs):
    """ Return the balance of an account for a given day."""
    sorted_balances = get_account_balances(accounts, account_id, day, *args, **kwargs)
    return get_balance(sorted_balances, day)

def get_account_balances(accounts, account_id, currency=None):
    """
    Returns all the balances of the account.
    Takes into account the `share` account property.

    @param currency if not None, conversion is applied
    @return a SortedDict of balances, None if no balance exist
    """
    balances = accounts[account_id].get('balances', None)
    if not balances:
        return None
    share = get_account_properties(accounts, account_id).get('share', 1)
    sorted_balance = SortedDict((date, value * share) for date, value in balances.items())
    no_change = get_account_properties(accounts, account_id).get('no_change', False)
    if no_change:
        first_day = sorted_balance.keys()[0]
        first_balance = sorted_balance[first_day]
        sorted_balance.clear()
        sorted_balance[first_day] = first_balance
        #for day, balance in sorted_balance.items():
        #    sorted_balance[day] = first_balance
    return sorted_balance

def get_accounts_balances(accounts, account_ids, *args, **kwargs):
    """
    Get balances of multiple accounts at once.
    Returned values are not "sum" of all accounts but lists of each account balance
    """
    sorted_dates = SortedDict()
    for account_id in account_ids:
        sorted_balances = get_account_balances(accounts, account_id, *args, **kwargs)
        if sorted_balances is None:
            continue
        sorted_dates.update(dict.fromkeys(sorted_balances.keys(), 0))
    for day in sorted_dates:
        balances = []
        for account_id in account_ids:
            balance = get_account_balance(accounts, account_id, day, *args, **kwargs)
            balances.append(balance)
        sorted_dates[day] = balances
    return sorted_dates

def filter_accounts(accounts, account_types):
    """
    @return a new dictionary with accounts belonging to account_types
    """
    return {account_id:account for (account_id,account) in accounts.items()
            if get_account_properties(accounts, account_id).get('account-type')
            in account_types}

def group_accounts(accounts, account_types=all_account_types.keys()):
    """
    Group accounts per account type
    @return an ordered dict of input accounts grouped by account type.
    """
    grouped_accounts = collections.OrderedDict()
    for account_type in [*account_types, 'other']:
        for account_id in accounts.keys():
            act = get_account_properties(accounts, account_id).get('account-type')
            if act == account_type or (account_type == 'other' and
               act not in account_types):
                grouped_accounts.setdefault(account_type, {})[account_id] = accounts[account_id]
    return grouped_accounts

def plot_balances(days, balances, end_day=None, interpolation='hermite', smooth=False, *args, **kwargs):
    """
    @param end_day if not None, a day is added at the end with the same balance of the last day
    @param interpolation Specify how to draw between points: 'post', 'pre', 'mid', 'hermite' or 'linear'
    @param smooth if True, apply 365 day smoothing window on balances. w
    """
    plotter = plt.plot

    first_day = days[0]
    last_day = days[-1]
    day_range = (last_day-first_day).days
    if len(days) < 4 or len(days) < 3 * day_range / 365:  # no more than semestrial balances
        plotter(days, balances, *args, linestyle='None', marker='o', alpha=0.5, **kwargs)

    if end_day is not None and last_day != end_day:
        days = days + tuple([end_day])
        balances = balances + tuple([balances[-1]])
        last_day = days[-1]

    if interpolation in ['post', 'pre', 'mid']:
        # Could also use interpolate.interp1d
        plotter = plt.step
        kwargs['where'] = interpolation
    elif interpolation == 'hermite' and len(days) > 3:
        plot_range = [first_day + datetime.timedelta(days=d) for d in range(0, (last_day-first_day).days)]
        # 1: linear:
        # f2 = interpolate.interp1d(toTimestamps(x), y, kind='linear')
        # x = plot_range
        # y = f2(toTimestamps(plot_range))
        # 2: Cubic spline:
        # spl = interpolate.splrep(toTimestamps(x), y, s=1)
        # x = plot_range
        # y = interpolate.splev(toTimestamps(plot_range), spl)
        # 3: Hermite interpolation
        balances = interpolate.pchip_interpolate(toTimestamps(days), balances, toTimestamps(plot_range))
        days = plot_range

        window_len = 365
        if smooth and len(balances) > window_len:
            # w=numpy.ones(window_len,'d')  # moving average
            # w=numpy.hanning(window_len)
            w=numpy.hamming(window_len)
            # w=numpy.blackman(window_len)
            balances = numpy.convolve(balances, w/w.sum(), mode='same')

    return plotter(days, balances, *args, **kwargs)

def plot_account(accounts, account_id, *args, **kwargs):
    sorted_balances = get_account_balances(accounts, account_id)
    if sorted_balances is None:
        return None

    days, balances = zip(*sorted_balances.items())

    return plot_balances(days, balances, *args, **kwargs)

def plot_accounts(accounts, ignored_categories=[], log_scale=False, stacked=False, total=False, subtotals=False, no_real_estate_appreciation=False):
    # Stack do not work with negative balances
    if stacked:
        ignored_categories.append('loan')
    account_types = [account_type for account_type in all_account_types.keys() if account_type not in ignored_categories]
    not_ignored_accounts = filter_accounts(accounts, account_types)

    # Group accounts per category type
    # TODO: key=account_type, value=list of account ids
    # {
    #   'checking': {
    #      'BNP-foo': {},
    #      'BPLC-bar': {},
    #   },
    #   'saving': {
    #      'LivretA': {},
    #      'PEL': {},
    #   },
    # }
    grouped_accounts = group_accounts(not_ignored_accounts)

    if no_real_estate_appreciation:
        all_account_types['real-estate']['account']['no_change'] = True

    plots = []
    labels = []

    # Compute total
    total_balances = get_accounts_balances(accounts, not_ignored_accounts.keys())
    last_day = total_balances.keys()[-1]
    print('Total of {:.2f}€ on {}'.format(sum(total_balances[last_day]), last_day))

    if stacked:
        fig, ax = plt.subplots()
    else:
        fig = plt.figure()

    # Plot accounts
    if not stacked and not subtotals:
        type_index = 0
        for account_type in grouped_accounts.keys():
            account_index = 0
            for account_id in grouped_accounts[account_type]:

                # todo some accounts may not have any balance
                # is_last_type = type_index == len(grouped_accounts) - 1
                # offset_sign = -1 if is_last_type else 1
                # color_index = type_index
                # if len(grouped_accounts[account_type]) > 1:
                #     color_index += offset_sign * 0.5 * account_index / (len(grouped_accounts[account_type])-1)

                # if len(grouped_accounts) > 1:
                #     color_index /= (len(grouped_accounts) - 1)

                # c = cm.rainbow(color_index)

                c = get_account_properties(accounts, account_id).get('color', 'lightgrey')

                plot = plot_account(accounts, account_id, end_day=last_day, color=c, label=account_id)
                if plot:
                    plots += plot
                    labels += [account_id]
                    account_index += 1
            type_index += 1

    if subtotals:
        for account_type in grouped_accounts.keys():
            group_balances = get_accounts_balances(accounts, grouped_accounts[account_type])
            days, balances = zip(*group_balances.items())
            c = get_account_properties(all_account_types, account_type).get('color', 'lightgrey')
            interpolation = 'hermite'
            if account_type == 'real-estate' and no_real_estate_appreciation:
                interpolation = 'post'
            plots += plot_balances(days, tuple(sum(b) for b in balances),
                                   end_day=last_day,
                                   interpolation=interpolation,
                                   color=c,
                                   label=account_type)
            labels += [account_type]

    # Plot total
    if total:
        if stacked:
            number_of_accounts = len(next(iter(total_balances.values())))
            colors = cm.rainbow(numpy.linspace(0, 1, number_of_accounts))
            values = list(map(list, zip(*total_balances.values())))
            ax.stackplot(total_balances.keys(),
                        list(map(list, zip(*total_balances.values()))),
                        labels=labels,
                        colors=colors)
        else:
            days, balances = zip(*total_balances.items())
            plots += plot_balances(days, tuple(sum(b) for b in balances), end_day=last_day, color='dimgrey', label='Total')
            labels += ['Total']
            plots += plot_balances(days, tuple(sum(b) for b in balances), end_day=last_day, smooth=True, color='black', linestyle='dashed', label='Smoothed Total')
            labels += ['Smoothed Total']

    # Plot legend
    if stacked:
        legend = ax.legend(loc='upper left')
    else:
        legend = plt.legend(plots, labels)

    lined = dict()
    for legline, origline in zip(legend.get_lines(), plots):
        legline.set_picker(5)  # 5 pts tolerance
        lined[legline] = origline

    def onpick(event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legline = event.artist
        origline = lined[legline]
        if origline.get_linewidth() == 4:
            origline.set_linewidth(1)
            origline.set_visible(False)
            origline.set_zorder(2)
            legline.set_linewidth(1)
            legline.set_alpha(0.2)
        elif origline.get_visible():
            origline.set_linewidth(4)
            origline.set_zorder(200)
            legline.set_linewidth(4)
        else:
            origline.set_visible(True)
            legline.set_alpha(1.0)
        # Change the alpha on the line in the legend so we can see what lines
        # have been toggled
        fig.canvas.draw()

    fig.canvas.mpl_connect('pick_event', onpick)

    # Scale plot
    if log_scale:
        plt.yscale('symlog')
        plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        plt.gca().yaxis.get_major_formatter().set_scientific(False)

    # Plot events
    for account_type in grouped_accounts.keys():
        for account_id in grouped_accounts[account_type]:
            events = accounts[account_id].get('events', {})
            for event_day in events:
                event = events[event_day]
                event_type = event.get('type', 'point')
                balance = event.get('balance', get_account_balance(accounts, account_id, event_day))
                if event_type == 'line':
                    plt.axvline(event_day)
                elif event_type == 'point':
                    plt.scatter([event_day], [balance], c='red')
                if event.get('label'):
                    plt.text(event_day, balance, event.get('label'))#,rotation=90)

    if not stacked:
        mplcursors.cursor().connect(
            "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        # format the coords message box
        plt.gca().format_xdata = mdates.DateFormatter('%Y-%m-%d')
        plt.gca().format_ydata = lambda x: '%1.2f' % x  # format the price.

        plt.gca().grid(True)

    plt.show()


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("file_or_folder",
                        help="a json file or a folder containing json files")
    parser.add_argument("-i", "--ignore", action='append', default=[],
                        help="Account type to ignore (e.g. -i loan -i real-estate)")
    parser.add_argument("--log", action="store_true",
                        help="Use log scale")
    parser.add_argument("--stack", action="store_true",
                        help="Stack accounts")
    parser.add_argument("--subtotals", action="store_true",
                        help="Plot totals per account type")
    parser.add_argument("--no_real_estate_appreciation", action="store_true",
                        help="If set, real_estate does not get appreciated")

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

    plot_accounts(accounts,
                  ignored_categories=args.ignore,
                  log_scale=args.log,
                  stacked=args.stack,
                  subtotals=args.subtotals,
                  no_real_estate_appreciation=args.no_real_estate_appreciation)

if __name__ == "__main__":
    sys.exit(main())
