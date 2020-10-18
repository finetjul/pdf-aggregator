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
python aggregate_accounts.py path/to/folder/with/PDF
```

or

```
python aggregate_accounts.py path/to/file.pdf
```

### Plot
Plot aggregated data:

```
python plot_accounts.py path/to/folder/with/multiple/accounts.json
```

or

```
python plot_accounts.py path/to/accounts.json
```
