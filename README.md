# PDF aggregator

Aggregate account PDF statements into JSON and visualize aggregated financial data as timeline.

![PDF aggregator](https://raw.githubusercontent.com/finetjul/pdf-aggregator/master/docs/pdf-aggregator.svg)

Works offline and relies on [tika](https://tika.apache.org/) for PDF parsing and [matplotlib](https://matplotlib.org/) for plotting.
It relies on regular expressions stored in simple configuration files to extract bank statements balance, date, account number...

## Installation

```
pip install -r requirements.txt
```

## Usage

### Aggregate
Scan PDF files and aggregate financial data into an accounts.json summary file:

```
python aggregator/aggregate.py path/to/folder/with/PDF
```

or

```
python aggregator/aggregate.py path/to/file.pdf
```

```--help``` for more options.

### Add a new config

```
python aggregator/aggregate.py path/to/PDF/file --test
```

It should print out the content of the pdf. Then test regular expression:

```
python aggregator/aggregate.py path/to/PDF/file --test 'Ending balance on (\d+)/(\d+)/(\d+)'
```

You can then create conf file and test detection with -vvv:

```
python aggregator/aggregate.py path/to/PDF/file -vvv
```


### Plot
Plot aggregated data:

```
python aggregator/plot.py path/to/folder/with/multiple/accounts.json
```

or

```
python aggregator/plot.py path/to/accounts.json
```

```--help``` for more options.

Example:

```
python.exe .\aggregator\plot.py .\accounts\ --subtotals --total --real-estate operations --filter f-currency=$
```
