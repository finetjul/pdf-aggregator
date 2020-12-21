# PDF aggregator

Aggregate account PDF statements into JSON and visualize aggregated financial data as timeline.
Works offline and relies on [tika](https://tika.apache.org/) for PDF parsing and [matplotlib](https://matplotlib.org/) for plotting.

![PDF aggregator](/doc/pdf-aggregator.svg)
## Installation

```
pip install -r requirements.txt
```

## Usage

### Aggregate
Scan PDF files and aggregate financial data into an accounts.json summary file:

```
python aggregate.py path/to/folder/with/PDF
```

or

```
python aggregate.py path/to/file.pdf
```

```--help``` for more options.

### Add a new config

```
python aggregate.py path/to/PDF/file --test
```

It should print out the content of the pdf. Then test regular expression:

```
python aggregate.py path/to/PDF/file --test 'Ending balance on (\d+)/(\d+)/(\d+)
```

You can then create conf file and test detection with -vvv:

```
python aggregate.py path/to/PDF/file -vvv
```


### Plot
Plot aggregated data:

```
python plot.py path/to/folder/with/multiple/accounts.json
```

or

```
python plot.py path/to/accounts.json
```

```--help``` for more options.

Example:

```
python.exe .\plot.py .\accounts\ --subtotals --no_real_estate_appreciation
```
