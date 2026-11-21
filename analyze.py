"""Superstore Sales Analysis — Week 1 bootcamp portfolio piece.

Answers five business questions with reproducible cleaning, aggregation,
and charts. Outputs: cleaned CSV, KPI JSON, and PNG figures in ../outputs/.
"""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "outputs"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "axes.grid": True, "grid.alpha": 0.3})

# ---------------- 1. Load & clean ----------------
df = pd.read_csv(DATA / "raw_superstore.csv", encoding="latin-1",
                 parse_dates=["Order Date", "Ship Date"])

n_raw = len(df)
df = df.drop_duplicates()                       # 0 duplicates found, rule kept for safety
df["Order Priority"] = df["Order Priority"].replace("Not Specified", pd.NA)
df["Month"] = df["Order Date"].dt.to_period("M")
df["Profit Margin %"] = (df["Profit"] / df["Sales"] * 100).round(1)
cleaning_log = {
    "rows_raw": n_raw, "rows_after_dedup": int(len(df)),
    "duplicate_rows_removed": int(n_raw - len(df)),
    "missing_values_per_column": {k: int(v) for k, v in df.isna().sum().items() if v > 0},
    "order_priority_repaired_to_missing": "Not Specified -> NaN",
    "derived_columns": ["Month", "Profit Margin %"],
}
df.to_csv(DATA / "superstore_clean.csv", index=False)

# ---------------- 2. KPIs ----------------
kpi = {
    "total_sales": round(df.Sales.sum(), 2),
    "total_profit": round(df.Profit.sum(), 2),
    "avg_order_value": round(df.Sales.sum() / df["Order ID"].nunique(), 2),
    "overall_margin_pct": round(float(df.Profit.sum() / df.Sales.sum() * 100), 1),
    "loss_line_share_pct": round(float((df.Profit < 0).mean() * 100), 1),
    "n_customers": int(df["Customer ID"].nunique()),
    "date_min": str(df["Order Date"].min().date()),
    "date_max": str(df["Order Date"].max().date()),
}
(OUT / "kpi.json").write_text(json.dumps({"kpi": kpi, "cleaning_log": cleaning_log},
                                         indent=2, default=float))

# ---------------- 3. Q1: Profit by category ----------------
cat = (df.groupby("Category")
         .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"),
              Margin=("Profit", lambda p: p.sum()))
         .assign(Margin=lambda d: (d.Profit / d.Sales * 100).round(1))
         .sort_values("Profit", ascending=False))
cat.to_csv(OUT / "profit_by_category.csv")

fig, ax = plt.subplots(figsize=(9, 4.5))
top = cat.head(10).iloc[::-1]
ax.barh(top.index, top.Profit, color="#2a9d8f")
ax.set_title("Top 10 product categories by total profit (2013-2016)")
ax.set_xlabel("Total profit ($)")
fig.tight_layout(); fig.savefig(OUT / "q1_profit_by_category.png"); fig.savefig(OUT / "q1_profit_by_category.svg"); plt.close(fig)

# ---------------- 4. Q2: Sales & profit by region ----------------
reg = (df.groupby("Region").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")))
reg["Margin %"] = (reg.Profit / reg.Sales * 100).round(1)
reg.to_csv(OUT / "region_performance.csv")

fig, ax = plt.subplots(figsize=(8, 4.5))
x = range(len(reg))
ax.bar([i - 0.2 for i in x], reg.Sales / 1e6, width=0.4, label="Sales ($M)", color="#264653")
ax.bar([i + 0.2 for i in x], reg.Profit / 1e6, width=0.4, label="Profit ($M)", color="#e9c46a")
ax.set_xticks(list(x)); ax.set_xticklabels(reg.index)
ax.set_title("Sales vs profit by region"); ax.set_ylabel("$ millions")
ax.legend()
fig.tight_layout(); fig.savefig(OUT / "q2_region.png"); fig.savefig(OUT / "q2_region.svg"); plt.close(fig)

# ---------------- 5. Q3: Discount vs profit relationship ----------------
disc = (df.groupby(pd.cut(df.Discount, [-.01, 0, .05, .10, .15, .20, 1],
                          labels=["0%", "<=5%", "6-10%", "11-15%", "16-20%", ">20%"]),
                  observed=True)
          .agg(mean_line_profit=("Profit", "mean"),
               loss_share=("Profit", lambda p: (p < 0).mean() * 100),
               lines=("Profit", "size")))
disc.round(1).to_csv(OUT / "discount_impact.csv")

fig, ax1 = plt.subplots(figsize=(8, 4.5))
ax2 = ax1.twinx()
ax1.bar(disc.index.astype(str), disc.mean_line_profit, color="#e76f51", label="Avg line profit ($)")
ax2.plot(disc.index.astype(str), disc.loss_share, "o-", color="#264653", label="Loss-making lines (%)")
ax1.axhline(0, color="grey", lw=0.8)
ax1.set_title("Discount tiers: average profit collapses as discounts rise")
ax1.set_ylabel("Avg profit per line ($)"); ax2.set_ylabel("Share of loss-making lines (%)")
lines1, lbl1 = ax1.get_legend_handles_labels(); lines2, lbl2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, lbl1 + lbl2, loc="upper right")
fig.tight_layout(); fig.savefig(OUT / "q3_discount_impact.png"); fig.savefig(OUT / "q3_discount_impact.svg"); plt.close(fig)

# ---------------- 6. Q4: Segment revenue ----------------
seg = (df.groupby("Customer Segment").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")))
seg["Sales share %"] = (seg.Sales / seg.Sales.sum() * 100).round(1)
seg.to_csv(OUT / "segment_performance.csv")

fig, ax = plt.subplots(figsize=(6.5, 4.5))
ax.pie(seg["Sales"], labels=seg.index, autopct="%1.1f%%",
       colors=["#264653", "#2a9d8f", "#e9c46a", "#f4a261"])
ax.set_title("Revenue share by customer segment")
fig.tight_layout(); fig.savefig(OUT / "q4_segment.png"); fig.savefig(OUT / "q4_segment.svg"); plt.close(fig)

# ---------------- 7. Q5: Monthly seasonality ----------------
monthly = df.groupby("Month").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
monthly.to_csv(OUT / "monthly_trend.csv")
yearly = df.groupby(df["Order Date"].dt.year)[["Sales", "Profit"]].sum()

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(monthly.index.to_timestamp(), monthly.Sales / 1e3, color="#264653", label="Sales ($K)")
ax.plot(monthly.index.to_timestamp(), monthly.Profit / 1e3 * 5, color="#2a9d8f", alpha=0.7,
        label="Profit ($K, x5 for scale)")
ax.set_title("Monthly sales trend, 2013-2016"); ax.set_ylabel("$ thousands")
ax.legend()
fig.tight_layout(); fig.savefig(OUT / "q5_monthly_trend.png"); fig.savefig(OUT / "q5_monthly_trend.svg"); plt.close(fig)

print("KPIs:", json.dumps(kpi, indent=2, default=float))
print("\nTop 5 categories by profit:\n", cat.head(5).to_string())
print("\nRegions:\n", reg.to_string())
print("\nDiscount tiers:\n", disc.round(1).to_string())
print("\nSegments:\n", seg.to_string())
print("\nYearly:\n", yearly.to_string())
print("\nWorst items by profit:\n",
      df.groupby("Item")[["Sales", "Profit"]].sum().nsmallest(5, "Profit").to_string())
print("\nDone. Outputs in", OUT)
