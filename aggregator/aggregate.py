import collections
import datetime
import dateutil.parser
import json
import os
import pathlib
import re
import sys
import tika.parser

debug = False

def memoize(f):
    memo = {}
    def helper(x):
        if x not in memo:
            memo[x] = f(x)
        return memo[x]
    return helper

@memoize
def read_confs(conf_file_path):
    """ read a json encoded file that must have the following format:
    {
        "BNP 2014": {
            "bank-name": "BNP",
            "bank-pattern": "BNP PARIBAS SA",
            "balance-pattern": "SOLDE CREDITEUR AU \\d\\d\\.\\d\\d\\.\\d\\d\\d\\d ([\\d ]+\\,\\d{2})",
            "date-pattern": "SOLDE CREDITEUR AU (\\d\\d)\\.(\\d\\d)\\.(\\d\\d\\d\\d)",
        },
        "BNP 2018": {
            "bank-name": "BNP",
            ...
        },
    }
    """
    with open(conf_file_path, encoding='utf-8') as conf_file:
        try:
            conf = json.load(conf_file)
        except:
            return None
        return conf

def get_conf_files(confs_path):
    """
    confs_path: folder that contains all the configuration files.
    Returns all the configuration files located in confs_path
    """
    conf_files = []
    for (dir_path, dir_names, file_names) in os.walk(confs_path):
        for file_name in file_names:
            if pathlib.Path(file_name).suffix == ".json":
                conf_files.append(os.path.join(dir_path, file_name))
    return conf_files

mandatory_patterns = ["bank-pattern", "account-pattern", "date-pattern"]

def search(pattern, text):
    """
    Convenient re.search function that takes a pattern or a list of patterns.
    Returns at the firt match
    """
    patterns = pattern if isinstance(pattern, list) else [pattern]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match

def findall(pattern, text):
    """
    Convenient re.findall function that takes a pattern or a list of patterns.
    Returns at the firt match
    """
    patterns = pattern if isinstance(pattern, list) else [pattern]
    for pattern in patterns:
        match = re.findall(pattern, text)
        if match:
            return match

@memoize
def parse_pdf(file_path):
    [stem, ext] = os.path.splitext(file_path)
    if ext != '.pdf':
        return None
    pdf_contents = tika.parser.from_file(file_path)
    return pdf_contents['content']

def find_confs(file_path, confs_path, verbose=0):
    bank_extract = parse_pdf(file_path)
    matching_confs = []
    if not bank_extract:
        return matching_confs
    for conf_file_path in get_conf_files(confs_path):
        confs = read_confs(conf_file_path)
        for conf_name in confs.keys():
            conf = confs[conf_name]
            if "bank-name" not in conf is None:
                continue
            searches = [search(conf[pattern], bank_extract)
                        for pattern in mandatory_patterns if pattern in conf]
            if all(searches):
                matching_confs.append(conf)
                continue
            if verbose >= 3:
                print("************\n{}():  Conf does not match bank extract\n"
                      "  Conf: {}\n  Search results: {}".format(
                    find_confs.__name__, conf, searches))
    if len(matching_confs) == 0 and verbose == 2:
        matching_confs = find_confs(bank_extract, confs_path, verbose + 1)
    return matching_confs

def parse_bank_extract(file_path, conf, verbose=0):
    bank_extract = parse_pdf(file_path)

    data = conf.copy()
    data.pop('bank-pattern', None)
    if "account-pattern" in conf:
        account = search(conf["account-pattern"], bank_extract)
        if account:
            account_value = conf.get('account-value', "{}")
            data['account'] = account_value.format(*account.groups())
        #data['account'] = re.sub(r"\s+", '', data['account'])
        data.pop('account-pattern', None)
        data.pop('account-value', None)
    elif verbose > 0:
        print('no account-pattern')
    if "balance-pattern" in conf:
        balance = findall(conf["balance-pattern"], bank_extract)
        if balance:
            balance_value = conf.get("balance-value", "{}.{}").format(*balance[-1])
            data['balance'] = float(re.sub(r"[\s,]+", '', balance_value))
        elif verbose > 0:
            print(os.path.basename(file_path), data['account'], "balance not found", bank_extract)
        data.pop('balance-pattern', None)
        data.pop('balance-value', None)
    elif "credit-pattern" in conf:
        credit = findall(conf["credit-pattern"], bank_extract)
        if credit:
            print('credit', credit)
            data['balance'] = float(re.sub(r"\s+", '', credit[-1]).replace(",", "."))
        elif "debit-pattern" in conf:
            debit = findall(conf["debit-pattern"], bank_extract)
            print('debit', debit)
            if debit:
                data['balance'] = -float(re.sub(r"\s+", '', debit[-1]).replace(",", "."))
            else:
                print("debit not found")
        elif verbose > 0:
            print("credit not found")
        data.pop('credit-pattern', None)
        data.pop('credit-value', None)
        data.pop('debit-pattern', None)
        data.pop('debit-value', None)
    elif verbose > 0:
        print('no credit-pattern')
    if "date-pattern" in conf:
        date = findall(conf["date-pattern"], bank_extract)
        if date:
            date_value = conf.get("date-value", "{2}-{1}-{0}").format(*date[-1])
            data['date'] = dateutil.parser.parse(date_value).date()
        elif verbose > 0:
            print("date not found")
        data.pop('date-pattern', None)
        data.pop('date-value', None)
    elif verbose > 0:
        print('no date-pattern')
        print(conf)
    return data


def aggregate_pdf(file_path, confs_path="./confs", verbose=0):
    accounts = collections.defaultdict(lambda: collections.defaultdict(dict))

    data = None
    confs = find_confs(file_path, confs_path, verbose)
    for conf in confs:
        data = parse_bank_extract(file_path, conf, verbose)
        if data is not None and 'date' in data and 'balance' in data:
            if verbose > 0:
                print(os.path.basename(file_path), data['date'], data['account'], data['balance'])
            account_id = "-".join([data['bank-name'], data['account']])
            account = accounts[account_id]['account']
            accounts[account_id]['balances'].update({
                data['date']: data['balance']
            })
            del data['date']
            del data['balance']
            account.update(data)
        elif verbose >= 3:
            print(data)
    if len(accounts) == 0:
        print(file_path, "skipped", file=sys.stderr)
    return accounts

def aggregate_pdfs(folder_path, confs_path="./confs", verbose=0):

    def update(d, u):
        """ Recursive dictionary update() """
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = update(d[k], v)
            else:
                d[k] = v
        return d

    accounts = collections.defaultdict(lambda: collections.defaultdict(dict))
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            path_to_pdf = os.path.join(root, file)
            try:
                pdf_accounts = aggregate_pdf(path_to_pdf, confs_path, verbose)
                update(accounts, pdf_accounts)
            except Exception as inst:
                print(path_to_pdf, inst)
                raise inst

    return accounts

def toJSON(accounts):
    def replace_keys(accounts):
        new_accounts = { }
        for key in accounts.keys():
            if isinstance(key, (datetime.date, datetime.datetime)):
                new_accounts[key.isoformat()] = accounts[key]
            elif isinstance(accounts[key], dict):
                new_accounts[key] = replace_keys(accounts[key])
            else:
                new_accounts[key] = accounts[key]
        return new_accounts 

    iso_accounts = replace_keys(accounts)
    return json.dumps(iso_accounts, indent = 2)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file_or_folder",
                        help="a pdf file or a folder containing pdf files")
    parser.add_argument("-c", "--confs", help="folder to find conf files",
                        default=os.path.join(os.path.dirname(os.path.realpath(__file__)), "confs"))
    parser.add_argument("-o", "--output", help="output json file to store aggregated file",
                        default="accounts.json")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase output verbosity (0: none, 1: light...)")
    parser.add_argument("--test", const='', nargs='?', help="test regular expression on pdf (do not double backslash '\' here)")

    args = parser.parse_args()

    if args.test is not None:
        pdf_contents = tika.parser.from_file(args.file_or_folder)
        bank_extract = pdf_contents['content']
        if args.test:
            res = findall(args.test, bank_extract)
            print("Apply '{}'\nResult: {}".format(args.test, res, bank_extract))
        else:
            print("Contents: {}".format(bank_extract))
    else:
        if pathlib.Path(args.file_or_folder).is_file():
            accounts = aggregate_pdf(args.file_or_folder, confs_path=args.confs, verbose=args.verbose)
        else:
            accounts = aggregate_pdfs(args.file_or_folder, confs_path=args.confs, verbose=args.verbose)

        accounts_json = toJSON(accounts)
        if args.verbose > 0:
            print(accounts_json)

        with open(args.output, 'w') as accounts_json_file:
            accounts_json_file.write(accounts_json)

if __name__ == "__main__":
    sys.exit(main())
