# Superstore Sales & Profitability Analysis

**Week 1 portfolio project** — Data Science & Analytics Intensive Bootcamp.
Exploratory analysis of the classic Tableau *Sample Superstore* retail dataset
(9,426 transactions, 2013–2016, 2,703 customers).

## Business questions

1. Which product categories earn the highest profit?
2. Which region performs best (and worst)?
3. Are discounts reducing profit?
4. Which customer segment generates the most revenue?
5. How do sales trend over time?

## Key findings

- **Overall**: $8.95M sales, $1.31M profit, **14.7% margin**, avg order value $1,387.
- **Best categories**: Telephones & Communication ($298K profit) and Binders
  ($227K at a 35.5% margin — the best margin in the top 5).
- **Best region**: Central (20.0% margin). **Worst**: South — 7.1% margin,
  roughly half the company average.
- **Discounts hurt**: average line profit falls from $185 at 0% discount to $97
  at 6–10%, and every line discounted above 15% in this data lost money.
- **Segments**: Corporate leads with 36.5% of revenue; Consumer is only 20.5%.
- **Seasonality**: sales grow year over year (2013 is a partial ramp-up year),
  with Q4 spikes visible in the monthly trend.
- **Loss concentration**: 48% of transaction lines are unprofitable; the five
  worst items (printers, videoconferencing units, furniture) lose up to $40K each.

## Charts

**Discounts destroy profit** — average line profit collapses as discounts rise (combo: bars = avg profit, line = loss share):

![](outputs/q3_discount_impact.png)

**Best and worst regions** — South earns half the company-average margin:

![](outputs/q2_region.png)

## Repo layout

```
├── README.md
├── requirements.txt
├── data/
│   ├── raw_superstore.csv       # source data — add via GitHub web upload (2.3 MB)
│   └── superstore_clean.csv     # cleaned dataset (written by src/analyze.py)
├── src/
│   └── analyze.py               # full pipeline: clean → KPIs → charts
└── outputs/
    ├── kpi.json                 # KPIs + cleaning log (provenance)
    ├── q1_profit_by_category.png
    ├── q2_region.png
    ├── q3_discount_impact.png
    ├── q4_segment.png
    ├── q5_monthly_trend.png
    └── *.csv                    # aggregated tables behind each chart
```

## Data cleaning decisions (src/analyze.py)

- Source CSV decoded as `latin-1` (non-UTF-8 characters in product names).
- Deduplicate on full rows: **0 duplicates found**; rule kept for reproducibility.
- `Order Priority == "Not Specified"` (1,881 rows) converted to a true missing
  value instead of a fake category.
- Zero missing values in all other columns.
- Derived fields: `Month` (order period) and `Profit Margin %` per line.
- Every decision is logged into `outputs/kpi.json` under `cleaning_log`.

## Reproduce

```bash
pip install -r requirements.txt
python src/analyze.py
```

All figures and tables are regenerated deterministically from `data/raw_superstore.csv`
(the source CSV is distributed in this repo's releases / can be re-added via the
Tableau Sample Superstore dataset).

## Data source

Tableau's public *Sample Superstore* training dataset
(the version distributed with "Learning Tableau 10", Packt Publishing).
License: intended for education and portfolio use.

## Skills demonstrated

Data cleaning with documented decisions · KPI design · groupby aggregation ·
visual exploratory analysis · insight storytelling for business stakeholders.
