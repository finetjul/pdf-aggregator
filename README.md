# PDF aggregator

Aggregate account PDF statements into JSON and plot aggregated financial data.

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
