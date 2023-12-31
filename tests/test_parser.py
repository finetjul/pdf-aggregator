import os
from aggregator import aggregate

def test_parse_pdf():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_pdf_path = os.path.join(dir_path, 'data', '20150910-BPLC-31512345678.pdf')
    parsed_pdf = aggregate.parse_pdf(test_pdf_path)
    print(parsed_pdf)

def test_find_confs():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_pdf_path = os.path.join(dir_path, 'data', '20150910-BPLC-31512345678.pdf')
    confs = aggregate.find_confs(test_pdf_path)
    bplc_conf_path = os.path.join(dir_path, '..', 'confs', 'bplc.json')
    bplc_conf = aggregate.read_confs(bplc_conf_path)
    assert len(confs) == 1
    assert confs[0] == bplc_conf['Checking-monthly']

def test_conf(test_pdf_path="C:\\Users\\julie\\Dropbox\\Administration\\Financing\\Boursorama\\Relevés\\20211029-Boursorama-Releve_compte.pdf"):
    if not test_pdf_path:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_pdf_path = os.path.join(dir_path, 'data', '20150910-BPLC-31512345678.pdf')
    confs = aggregate.find_confs(test_pdf_path)
    for conf in confs:
        parsed_pdf = aggregate.parse_pdf(test_pdf_path, conf.get('parser'))
        parsed = aggregate.parse_bank_extract(parsed_pdf, conf)
        print(parsed)

def test_extract_pattern():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_pdf_path = os.path.join(dir_path, 'data', '20150910-BPLC-31512345678.pdf')
    bplc_confs = aggregate.find_confs(test_pdf_path)
    conf = bplc_confs[0]
    parsed_pdf = aggregate.parse_pdf(test_pdf_path, conf.get('parser'))
    credit = aggregate.extract_pattern("credit", conf, parsed_pdf, conf)
    assert credit == 75

def test_parse_bank_extract():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_pdf_path = os.path.join(dir_path, 'data', '20150910-BPLC-31512345678.pdf')
    bplc_confs = aggregate.find_confs(test_pdf_path)
    conf = bplc_confs[0]
    parsed_pdf = aggregate.parse_pdf(test_pdf_path, conf.get('parser'))
    parsed = aggregate.parse_bank_extract(parsed_pdf, conf)
    print(parsed)
    assert parsed['balance'] == 75

