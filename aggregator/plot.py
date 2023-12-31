import calendar
import collections
import datetime
import dateutil.parser
import json
import functools
import matplotlib as mpl
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

try:
    from utils import memoize_with_id, memoize_with_ids, cprofile, memoize_2
except:
    from .utils import memoize_with_id, memoize_with_ids, cprofile, memoize_2

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

    try:
        accountsJSON = json.load(accounts_file)
    except Exception as e:
        print('while loading', accounts_file)
        raise e
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
    }, 'crowd-funding': {
         'account': {
            'color': 'green',
            'input': 'operations'
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

@memoize_with_id
def toTimestamps(days):
    return [toTimestamp(d) for d in days]


def get_balance_exact(sorted_balances, day):
    if sorted_balances.keys()[0] > day:
        return 0
    index = sorted_balances.bisect(day)
    # last value if day is after last account entry
    index -= 1
    key = sorted_balances.iloc[index]
    return sorted_balances[key]

@memoize_2
def get_balance(sorted_balances, day):
    """
    Return the balance for a given day. Existing or not.
    Balance is Hermite interpolated.
    """
    #print('get_balance', id(sorted_balances), day)
    days = toTimestamps(sorted_balances.keys())

    # 1: Hermite interpolation:
    if len(days) > 3 and toTimestamp(day) >= days[0] and toTimestamp(day) <= days[-1]:
        f = interpolate.PchipInterpolator(days, sorted_balances.values())
        return f(toTimestamp(day))

    if len(days) != len(sorted_balances.values()):
        days = toTimestamps(sorted_balances.keys())
    # 2: linear interpolation:
    return numpy.interp(toTimestamp(day), days, sorted_balances.values(), 0)

    # if sorted_balances.keys()[0] > day:
    #     return 0
    # index = sorted_balances.bisect(day)
    # # last value if day is after last account entry
    # index -= 1
    # key = sorted_balances.iloc[index]
    # return sorted_balances[key]

def get_yearly_balance(sorted_balances, day):
    first_day_of_the_year = day.replace(month=1, day=1)
    balance_first_day_of_the_year = get_balance(sorted_balances, first_day_of_the_year)
    return get_balance(sorted_balances, day) - balance_first_day_of_the_year

def get_account_balance(accounts, account_id, day, *args, **kwargs):
    """ Return the balance of an account for a given day."""
    sorted_balances = get_account_balances(accounts, account_id, *args, **kwargs)
    balance_at_day = get_balance(sorted_balances, day)
    return balance_at_day

@memoize_2
def get_account_balances(accounts, account_id, yearly=False, currency=None):
    """
    Returns all the balances of the account.
    Takes into account the `share` account property.

    @param yearly if True, balance is reset on January firsts
    @param currency if not None, conversion is applied
    @return a SortedDict of balances, None if no balance exist
    """
    balances = accounts[account_id].get('balances', None)
    share = get_account_properties(accounts, account_id).get('share', 1)
    if not balances:
        sorted_balance = SortedDict()
    else:
        sorted_balance = SortedDict((date, value * share) for date, value in balances.items())
    #no_change = get_account_properties(accounts, account_id).get('no_change', False)
    input = get_account_properties(accounts, account_id).get('input', 'balances')
    if input == 'operations' or not balances:
        operations = accounts[account_id].get('operations', None)
        if operations:
            sorted_operations = SortedDict((date, value * share) for date, value in operations.items())
            operation_first_day = sorted_operations.keys()[0]
        else:
            sorted_operations = SortedDict()
            operation_first_day = datetime.datetime.max
        # operation first day is optional, use balance in that case
        if sorted_balance:
            balance_first_day = sorted_balance.keys()[0]
            if balance_first_day < operation_first_day:
                sorted_operations[balance_first_day] = sorted_balance[balance_first_day]
            sorted_balance.clear()
        dates = sorted_operations.keys()
        for i, date in enumerate(dates):
            sorted_balance[date] = sorted_operations[date] + sorted_balance.get(dates[i - 1], 0)
        #for day, balance in sorted_balance.items():
        #    sorted_balance[day] = first_balance
    if yearly:
        sorted_yearly_balances = SortedDict()
        for day in sorted_balance.keys():
            first_day_of_the_year = day.replace(month=1, day=1)
            last_day_of_previous_year = first_day_of_the_year - datetime.timedelta(days = 1 )
            yearly_balance_last_day_of_the_year = get_yearly_balance(sorted_balance, last_day_of_previous_year)
            if yearly_balance_last_day_of_the_year != 0:
                sorted_yearly_balances[last_day_of_previous_year] = yearly_balance_last_day_of_the_year
                sorted_yearly_balances[first_day_of_the_year] = 0
            sorted_yearly_balances[day] = get_yearly_balance(sorted_balance, day)
        sorted_balance = sorted_yearly_balances
    #print(account_id, input, sorted_balance)

    return sorted_balance

def get_accounts_balances(accounts, account_ids, *args, **kwargs):
    """
    Get balances of multiple accounts at once.
    Returned values are not "sum" of all accounts but lists of each account balance
    """
    sorted_dates = SortedDict()
    # First get only the dates
    for account_id in account_ids:
        sorted_balances = get_account_balances(accounts, account_id, *args, **kwargs)
        if sorted_balances is None:
            continue
        sorted_dates.update(dict.fromkeys(sorted_balances.keys(), 0))

    # For each date, compute the balance for each accounts
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
    Group accounts per category type.
    TODO: key=account_type, value=list of account ids
    {
      'checking': {
        'BNP-foo': {},
        'BPLC-bar': {},
      },
      'saving': {
        'LivretA': {},
        'PEL': {},
      },
    }
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
    # draw markers
    if (len(days) < 4 or len(days) < 3 * day_range / 365):  # no more than semestrial balances
        markersArgs = {'linestyle':'None', 'marker': 'o', 'alpha': 0.5} | kwargs
        plotter(days, balances, *args, **markersArgs)

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

def offset_day(day, index, count):
    number_of_days_per_year = day.replace(month=12, day=1) - day.replace(month=1, day=1)
    width = number_of_days_per_year / count
    return day + width * (index + 0.5)

def plot_balances_yearly(days, balances, index, count, *args, **kwargs):
    width = 366 / count
    return plt.bar([offset_day(d, index, count) for d in days], balances, round(width), *args, **kwargs)

def plot_account(accounts, account_id, *args, **kwargs):
    sorted_balances = get_account_balances(accounts, account_id)
    return plot_sorted_balances(sorted_balances, *args, **kwargs)

def plot_sorted_balances(sorted_balances, yearly=False, balance_operator=None, *args, **kwargs):
    if sorted_balances is None:
        return None
    if balance_operator:
        for day in sorted_balances.keys():
            sorted_balances[day] = balance_operator(sorted_balances[day])
    if yearly:
        first_period_first_day = sorted_balances.keys()[0].replace(month=1, day=1)
        first_period_last_day = sorted_balances.keys()[0].replace(month=12, day=31)
        last_period_last_day = sorted_balances.keys()[-1].replace(month=12, day=31)
        number_of_days_per_year = 365.2425
        years = round((last_period_last_day-first_period_last_day).days / number_of_days_per_year) + 1
        periods_first_days = [first_period_first_day.replace(year=(first_period_first_day.year+year)) for year in range(years)]
        periods_last_days = [first_period_last_day.replace(year=(first_period_last_day.year+year)) for year in range(years)]
        balances = [get_balance_exact(sorted_balances, year_last_day) for year_last_day in periods_last_days]
        if yearly == "relative":
            balances = [balance - (balances[i - 1] if i else 0) for i, balance in enumerate(balances)]
        plot = plot_balances_yearly(periods_first_days, balances, *args, **kwargs)
    else:
        days, balances = zip(*sorted_balances.items())
        plot = plot_balances(days, balances, *args, **kwargs)

    return plot

legend_elements = dict()
def setup_picking(fig, legend, plots):
    for legend_line, original_line in zip(legend.get_lines(), plots):
        legend_line.set_picker(5)  # 5 pts tolerance
        legend_elements[legend_line] = original_line
    for legend_patch, plot in zip(legend.get_patches(), plots):
        legend_patch.set_picker(5)  # 5 pts tolerance
        legend_elements[legend_patch] = plot

    def onpick(event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legend_element = event.artist
        picked_plot = legend_elements[legend_element]
        picked_plots = picked_plot.get_children() if type(picked_plot) == mpl.container.BarContainer else [picked_plot]
        artist_properties = {
            mpl.lines.Line2D: [{
                'plot': {
                    'linewidth': 1,  # line_width ?
                    'visible': True,
                    'zorder': 2
                },
                'legend': {
                    'linewidth': 1,  # line_width ?
                    'alpha': None
                }
            },
            {
                'plot': {
                    'linewidth': 4,  # line_width ?
                    'visible': True,
                    'zorder': 200
                },
                'legend': {
                    'linewidth': 4,  # line_width ?
                    'alpha': None
                }
            },
            {
                'plot': {
                    'linewidth': 1,  # line_width ?
                    'visible': False,
                    'zorder': 2
                },
                'legend': {
                    'linewidth': 1,  # line_width ?
                    'alpha': 0.2
                }
            }],
            mpl.container.BarContainer: [{
                'plot': {
                    'alpha': 1,
                    'visible': True
                },
                'legend': {
                    'alpha': None
                }
            },
            {
                'plot': {
                    'alpha': 0.4,
                    'visible': True
                },
                'legend': {
                    'alpha': 0.3
                }
            },
            {
                'plot': {
                    'alpha': 1,
                    'visible': False,
                },
                'legend': {
                    'alpha': 0.15
                }
            }]
        }
        artist_property = artist_properties[type(picked_plot)]
        level = 0
        for l in artist_property:
            is_level = True
            for prop, value in l['legend'].items():
                is_level = is_level and getattr(legend_element, 'get_' + prop)() == value
            if is_level:
                break
            level += 1
        next_level = (level + 1) % 3
        for prop, value in artist_property[next_level]['plot'].items():
            for p in picked_plots:
                getattr(p, 'set_' + prop)(value)
        for prop, value in artist_property[next_level]['legend'].items():
            getattr(legend_element, 'set_' + prop)(value)

        # Change the alpha on the line in the legend so we can see what lines
        # have been toggled
        fig.canvas.draw()

    fig.canvas.mpl_connect('pick_event', onpick)

def plot_accounts_yearly(accounts, ignored_categories=[],
                  log_scale=False,
                  yearly="absolute",
                  total=False,
                  subtotals=False,
                  account_input_types={}, #no_real_estate_appreciation=False,
                  start=None, end=None):
    account_types = [account_type for account_type in all_account_types.keys() if account_type not in ignored_categories]
    not_ignored_accounts = filter_accounts(accounts, account_types)
    not_ignored_accounts_count = len(not_ignored_accounts)
    grouped_accounts = group_accounts(not_ignored_accounts)

    for account_type, input in account_input_types.items():
        if input:
            all_account_types[account_type]['account']['input'] = input
    plots = []
    labels = []
    fig = plt.figure()
    type_index = 0
    account_index = 0

    plot_count = len(grouped_accounts) if subtotals else not_ignored_accounts_count
    if total:
        plot_count += 1

    for account_type in grouped_accounts.keys():
        if subtotals:
            group_balances = get_accounts_balances(accounts, grouped_accounts[account_type])
            #days, balances = zip(*group_balances.items())
            c = get_account_properties(all_account_types, account_type).get('color', 'lightgrey')
            #input = get_account_properties(all_account_types, account_type).get('input')
            plot = plot_sorted_balances(group_balances,
                                    yearly=yearly,
                                    balance_operator=sum,
                                    index=account_index,
                                    count=plot_count,
                                    color=c,
                                    label=account_type)
            if plot:
                plots += plot
                labels += [account_type]
                account_index += 1
        else:
            for account_id in grouped_accounts[account_type]:
                c = get_account_properties(accounts, account_id).get('color', 'lightgrey')
                #input = get_account_properties(accounts, account_id).get('input')
                plot = plot_account(accounts, account_id, yearly=yearly, index=account_index, count=plot_count, color=c, label=account_id)
                if plot:
                    plots.append(plot)
                    labels += [account_id]
                    account_index += 1
            type_index += 1

    if total:
        total_balances = get_accounts_balances(accounts, not_ignored_accounts.keys())
        last_day = total_balances.keys()[-1]
        print('Total of {:.2f}€ on {}'.format(sum(total_balances[last_day]), last_day))

        total_plot = plot_sorted_balances(total_balances,
                                      yearly=yearly,
                                      balance_operator=sum,
                                      index=plot_count-1,
                                      count=plot_count,
                                      color='dimgrey', label='Total')
        plots.append(total_plot)
        labels += ['Total']

    # Plot legend
    #plt.legend(plots, labels)
    legend = plt.legend()

    setup_picking(fig, legend, plots)

    # Scale plot
    if log_scale:
        plt.yscale('symlog')
        plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        plt.gca().yaxis.get_major_formatter().set_scientific(False)

    mplcursors.cursor().connect(
        "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

    # format the coords message box
    plt.gca().format_xdata = mdates.DateFormatter('%Y-%m-%d')
    plt.gca().format_ydata = lambda x: '%1.2f' % x  # format the price.

    #plt.gca().grid(True)
    plt.xlim(start, end)
    plt.show()

def plot_accounts(accounts, ignored_categories=[],
                  log_scale=False, stacked=False, total=False, subtotals=False,
                  account_input_types={}, #no_real_estate_appreciation=False,
                  start=None, end=None):
    # Stack do not work with negative balances
    if stacked:
        ignored_categories.append('loan')
    account_types = [account_type for account_type in all_account_types.keys() if account_type not in ignored_categories]
    not_ignored_accounts = filter_accounts(accounts, account_types)

    grouped_accounts = group_accounts(not_ignored_accounts)

    for account_type, input in account_input_types.items():
        if input:
            all_account_types[account_type]['account']['input'] = input
    #if no_real_estate_appreciation:
    #    all_account_types['real-estate']['account']['no_change'] = True

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
                print('>>>', account_id)
                input = get_account_properties(accounts, account_id).get('input')
                interpolation = 'post' if input == 'operations' else 'hermite' 
                plot = plot_account(accounts, account_id,
                    end_day=last_day, interpolation=interpolation, color=c, label=account_id)
                if plot:
                    plots += plot
                    labels.append(account_id)
                    account_index += 1
            type_index += 1

    if subtotals:
        for account_type in grouped_accounts.keys():
            group_balances = get_accounts_balances(accounts, grouped_accounts[account_type])
            days, balances = zip(*group_balances.items())
            c = get_account_properties(all_account_types, account_type).get('color', 'lightgrey')
            input = get_account_properties(all_account_types, account_type).get('input')
            interpolation = 'post' if input == 'operations' else 'hermite' 
            plot = plot_balances(days, tuple(sum(b) for b in balances),
                                   end_day=last_day,
                                   interpolation=interpolation,
                                   color=c,
                                   label=account_type)
            plots += plot
            labels.append(account_type)

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
            plot = plot_balances(days, tuple(sum(b) for b in balances), end_day=last_day, color='dimgrey', label='Total')
            plots += plot
            labels.append('Total')
            plot = plot_balances(days, tuple(sum(b) for b in balances), end_day=last_day, smooth=True, color='black', linestyle='dashed', label='Smoothed Total')
            plots += plot
            labels.append('Smoothed Total')

    # Plot legend
    if stacked:
        legend = ax.legend(loc='upper left')
    else:
        legend = plt.legend(plots, labels)

    setup_picking(fig, legend, plots)

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
                eventDict = event if type(event) is dict else {'label': event}
                event_type = eventDict.get('type', 'point')
                print(event_day, get_account_balance(accounts, account_id, event_day))
                balance = eventDict.get('balance', get_account_balance(accounts, account_id, event_day))
                if event_type == 'line':
                    plt.axvline(event_day)
                elif event_type == 'point':
                    plt.scatter([event_day], [balance], c='red')
                if eventDict.get('label'):
                    plt.text(event_day, balance, eventDict.get('label'))#,rotation=90)

    if not stacked:
        mplcursors.cursor().connect(
            "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        # format the coords message box
        plt.gca().format_xdata = mdates.DateFormatter('%Y-%m-%d')
        plt.gca().format_ydata = lambda x: '%1.2f' % x  # format the price.

        plt.gca().grid(True)

    plt.xlim(start, end)
    plt.show()


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("file_or_folder", nargs='+',
                        help="one or multiple json files or folders containing json files")
    parser.add_argument("-i", "--ignore", action='append', default=[],
                        help="Account type to ignore (e.g. -i loan -i real-estate)")
    parser.add_argument("--log", action="store_true",
                        help="Use log scale")
    parser.add_argument("--stack", action="store_true",
                        help="Stack accounts")
    parser.add_argument("--yearly", choices=['absolute', 'relative'],
                        default='no',nargs='?',
                        help="Reset balance each year. with no argument, absolute is considered")
    parser.add_argument("--total", action="store_true",
                        help="Plot total")
    parser.add_argument("--subtotals", action="store_true",
                        help="Plot totals per account type")
    # parser.add_argument("--no_real_estate_appreciation", action="store_true",
    #                     help="If set, real_estate does not get appreciated")
    for account_type in all_account_types.keys():
        parser.add_argument("--" + account_type, choices=['balances', 'operations'],
                            help="Consider true balance or I/O operations. For a closing 'operations'"
                             "(e.g. selling a real estate), please create a fake operation that adds"
                             "capital gain the day before the day of the closing operation (that brings balance to 0)"
                             "For example, if you buy a house 100K, and sell it 150K, you would then have 3"
                             "operations: +100K, +50K, -150K")
    parser.add_argument("--start", type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'),
                        help="Start plotting from given date")
    parser.add_argument("--end", type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'),
                        help="Stop plotting at given date")

    args = parser.parse_args()

    accounts = {}
    for file_or_folder in args.file_or_folder:
        if pathlib.Path(file_or_folder).is_file():
            accounts.update(readAccounts(file_or_folder))
        else:
            for root, dirs, files in os.walk(file_or_folder):
                for file in files:
                    accounts_file_path = os.path.join(root, file)
                    [stem, ext] = os.path.splitext(accounts_file_path)
                    if ext == '.json':
                        accounts.update(readAccounts(accounts_file_path))

    account_input_types = {}
    args_dict = vars(args)
    for account_type in all_account_types.keys():
        account_input_types[account_type] = args_dict.get(account_type.replace('-', '_'))
    print(account_input_types)
    if args.yearly is None:
        args.yearly = 'absolute'
    elif args.yearly == 'no':
        args.yearly = False
    if args.yearly:
        plot_accounts_yearly(accounts,
                  ignored_categories=args.ignore,
                  log_scale=args.log,
                  yearly=args.yearly,
                  total=args.total,
                  subtotals=args.subtotals,
                  # no_real_estate_appreciation=args.no_real_estate_appreciation,
                  account_input_types=account_input_types,
                  start=args.start, end=args.end)
    else:
        plot_accounts(accounts,
                  ignored_categories=args.ignore,
                  log_scale=args.log,
                  stacked=args.stack,
                  total=args.total,
                  subtotals=args.subtotals,
                  # no_real_estate_appreciation=args.no_real_estate_appreciation,
                  account_input_types=account_input_types,
                  start=args.start, end=args.end)

if __name__ == "__main__":
    import sys
    sys.exit(main())
