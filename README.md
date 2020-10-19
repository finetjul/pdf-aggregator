# PDF aggregator

Aggregate account PDF statements into JSON and visualize aggregated financial data as timeline.
Works offline and relies on [tika](https://tika.apache.org/) for PDF parsing and [matplotlib](https://matplotlib.org/) for plotting.

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
