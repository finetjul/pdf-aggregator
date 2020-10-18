import collections
import datetime
import dateutil.parser
import json
import os
import pathlib
import re
from tika import parser

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

def find_conf(bank_extract, confs_path, verbose=False):
    for conf_file_path in get_conf_files(confs_path):
        confs = read_confs(conf_file_path)
        for conf_name in confs.keys():
            conf = confs[conf_name]
            if "bank-name" not in conf is None:
                continue
            searches = [search(conf[pattern], bank_extract)
                        for pattern in mandatory_patterns if pattern in conf]
            if all(searches):
                return conf
            elif verbose:
                print(conf, searches, bank_extract)
    if debug and not verbose:
        find_conf(bank_extract, confs_path, True)
    return None

def parse_bank_extract(bank_extract, confs_path):
    conf = find_conf(bank_extract, confs_path)
    if conf is None:
        return None
    data = conf.copy()
    data.pop('bank-pattern', None)
    if "account-pattern" in conf:
        account = search(conf["account-pattern"], bank_extract)
        if account:
            account_value = conf.get('account-value', "{}")
            data['account'] = account_value.format(*account.groups())
        data['account'] = re.sub(r"\s+", '', data['account'])
        data.pop('account-pattern', None)
        data.pop('account-value', None)
    else:
        print('no account-pattern')
    if "balance-pattern" in conf:
        balance = findall(conf["balance-pattern"], bank_extract)
        if balance:
            balance_value = conf.get("balance-value", "{}.{}").format(*balance[-1])
            data['balance'] = float(re.sub(r"\s+", '', balance_value))
        else:
            print("balance not found", bank_extract)
        data.pop('balance-pattern', None)
        data.pop('balance-value', None)
    elif "credit-pattern" in conf:
        credit = findall(conf["credit-pattern"], bank_extract)
        if credit:
            data['balance'] = float(re.sub(r"\s+", '', credit[-1]).replace(",", "."))
        elif "debit-pattern" in conf:
            debit = findall(conf["debit-pattern"], bank_extract)
            if debit:
                data['balance'] = -float(re.sub(r"\s+", '', debit[-1]).replace(",", "."))
            else:
                print("debit not found")
        else:
            print("credit not found")
        data.pop('credit-pattern', None)
        data.pop('credit-value', None)
        data.pop('debit-pattern', None)
        data.pop('debit-value', None)
    else:
        print('no credit-pattern')
    if "date-pattern" in conf:
        date = findall(conf["date-pattern"], bank_extract)
        if date:
            date_value = conf.get("date-value", "{2}-{1}-{0}").format(*date[-1])
            data['date'] = dateutil.parser.parse(date_value).date()
        else:
            print("date not found")
        data.pop('date-pattern', None)
        data.pop('date-value', None)
    else:
        print('no date-pattern')
        print(conf)
    return data

def extract(folder_path, confs_path="./confs"):
    accounts = collections.defaultdict(lambda: collections.defaultdict(dict))
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            path_to_pdf = os.path.join(root, file)
            [stem, ext] = os.path.splitext(path_to_pdf)
            if ext == '.pdf':
                pdf_contents = parser.from_file(path_to_pdf)
                bank_extract = pdf_contents['content']
                data = parse_bank_extract(bank_extract, confs_path) if bank_extract else None
                if data is None:
                    print(path_to_pdf, "skipped")
                else:
                    if 'date' in data and 'balance' in data:
                        print(path_to_pdf, data['date'], data['balance'])
                        account_id = "-".join([data['bank-name'], data['account']])
                        account = accounts[account_id]['account']
                        accounts[account_id]['balances'].update({
                            data['date']: data['balance']
                        })
                        del data['date']
                        del data['balance']
                        account.update(data)

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

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: folder to extract")
        sys.exit(2)

    accounts = extract(sys.argv[1])

    accounts_json = toJSON(accounts)
    print(accounts_json)
    output_file = sys.argv[2] if len(sys.argv) >= 3 else "accounts.json"
    with open(output_file, 'w') as accounts_json_file:
        accounts_json_file.write(accounts_json)
