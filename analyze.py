"""Superstore Sales & Profitability Analysis.

Input : raw_superstore.csv (Packt "Learning Tableau 10" Superstore.csv, 9,426 lines)
Output: KPIs + data audit (kpi.json), tables (*.csv), charts (q1-q5 *.png),
        superstore_clean.csv (git-ignored, regenerable)

Run:  python analyze.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).resolve().parent
DARK, ACCENT, GREY, LIGHT = "#264653", "#e76f51", "#8d99ae", "#cfd8dc"
plt.rcParams.update({"figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlelocation": "left", "axes.titleweight": "bold", "font.size": 10,
                     "text.parse_math": False})   # so "$" prints as a dollar sign


def save(fig, name):
    fig.tight_layout()
    fig.savefig(ROOT / f"{name}.png")
    plt.close(fig)


# ---------------- 1. Load & audit ----------------
df = pd.read_csv(ROOT / "raw_superstore.csv", encoding="latin-1",
                 parse_dates=["Order Date", "Ship Date"])
n_raw = len(df)
dups = int(df.duplicated().sum())
df = df.drop_duplicates()

audit = {
    "rows_raw": n_raw,
    "duplicate_rows_removed": dups,
    "order_priority_not_specified_to_missing": int((df["Order Priority"] == "Not Specified").sum()),
    # Row ID in the publisher's file holds dates (e.g. 11/18/1951), not IDs -> unusable, dropped
    "row_id_is_not_an_id": bool(df["Row ID"].astype(str).str.contains("/").all()),
    # The same Order ID appears on different order dates (even different years)
    "order_ids_spanning_multiple_dates": int((df.groupby("Order ID")["Order Date"].nunique() > 1).sum()),
    "order_ids_total": int(df["Order ID"].nunique()),
    "lines_profit_exceeds_sales": int((df.Profit > df.Sales).sum()),
    "lines_shipped_over_30_days_after_order": int(((df["Ship Date"] - df["Order Date"]).dt.days > 30).sum()),
    "lines_shipped_before_order": int((df["Ship Date"] < df["Order Date"]).sum()),
}
df["Order Priority"] = df["Order Priority"].replace("Not Specified", pd.NA)
df = df.drop(columns="Row ID")
# An order = Order ID + Order Date (Order ID alone is reused across dates in this file)
df["Order Key"] = df["Order ID"].astype(str) + "_" + df["Order Date"].dt.strftime("%Y-%m-%d")
df["Month"] = df["Order Date"].dt.to_period("M")
df["Profit Margin %"] = (df.Profit / df.Sales * 100).round(1)
df["Discount Tier"] = pd.cut(df.Discount, [-.01, 0, .05, .10, 1], labels=["0%", "1-5%", "6-10%", ">10%"])

months = pd.period_range("2013-01", "2016-12", freq="M")
monthly = df.groupby("Month").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).reindex(months)
audit["months_with_no_orders"] = [str(m) for m in monthly.index[monthly.Sales.isna()]]
audit["months_under_10k_sales_incl_empty"] = int((monthly.Sales.fillna(0) < 10_000).sum())
audit["missing_values_after_cleaning"] = {k: int(v) for k, v in df.isna().sum().items() if v > 0}
df.drop(columns="Discount Tier").to_csv(ROOT / "superstore_clean.csv", index=False)

# ---------------- 2. KPIs ----------------
S, P = df.Sales.sum(), df.Profit.sum()
margin = P / S * 100
kpi = {
    "total_sales": int(S), "total_profit": int(P),
    "overall_margin_pct": round(float(margin), 1),
    "lines": int(len(df)), "orders": int(df["Order Key"].nunique()),
    "avg_order_value": round(float(S / df["Order Key"].nunique()), 2),
    "customers": int(df["Customer ID"].nunique()),
    "loss_line_share_pct": round(float((df.Profit < 0).mean() * 100), 1),
    "date_min": str(df["Order Date"].min().date()), "date_max": str(df["Order Date"].max().date()),
}

# ---------------- 3. Q1: profit by sub-category (all 17) ----------------
cat = df.groupby("Category").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"),
                                 Lines=("Sales", "size"), Avg_Discount=("Discount", "mean"))
cat["Margin %"] = (cat.Profit / cat.Sales * 100).round(1)
cat = cat.sort_values("Profit")
cat.round(3).to_csv(ROOT / "profit_by_category.csv")
losers = cat[cat.Profit < 0]
big_losers = losers[losers.Sales > 100_000]

fig, ax = plt.subplots(figsize=(9.5, 6))
ax.barh(cat.index, cat.Profit / 1e3, color=[ACCENT if p < 0 else DARK for p in cat.Profit])
for y, (p, m) in enumerate(zip(cat.Profit, cat["Margin %"])):
    ax.text(p / 1e3 + (4 if p >= 0 else -4), y, f"{m:.0f}% margin", va="center",
            ha="left" if p >= 0 else "right", fontsize=7.5, color=GREY)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlim(cat.Profit.min() / 1e3 - 45, cat.Profit.max() / 1e3 + 55)
ax.set_xlabel("Total profit, 2013-2016 ($ thousands)")
ax.set_title(f"{' & '.join(big_losers.index)} lose ${-big_losers.Profit.sum() / 1e3:.0f}K "
             f"on ${big_losers.Sales.sum() / 1e6:.2f}M of sales")
save(fig, "q1_profit_by_category")

# ---------------- 4. Q2: margin by region ----------------
reg = df.groupby("Region").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
reg["Margin %"] = (reg.Profit / reg.Sales * 100).round(1)
reg = reg.sort_values("Margin %", ascending=False)
reg.to_csv(ROOT / "region_performance.csv")
# South gap: profit South would make at the other regions' margin, sub-category by sub-category
south = df[df.Region == "South"].groupby("Category")[["Sales", "Profit"]].sum()
rest = df[df.Region != "South"].groupby("Category")[["Sales", "Profit"]].sum()
south["gap"] = south.Sales * (rest.Profit / rest.Sales).reindex(south.index) - south.Profit
south.sort_values("gap", ascending=False).round(0).to_csv(ROOT / "south_gap_by_category.csv")

fig, ax = plt.subplots(figsize=(8, 4.3))
ax.bar(reg.index, reg["Margin %"], color=[ACCENT if r == "South" else DARK for r in reg.index])
ax.axhline(margin, color=GREY, ls="--", lw=1)
ax.text(len(reg) - 0.5, margin + 0.4, f"company {margin:.1f}%", ha="right", fontsize=8, color=GREY)
for x, (m, s) in enumerate(zip(reg["Margin %"], reg.Sales)):
    ax.text(x, m + 0.4, f"{m:.1f}%\n(${s / 1e6:.1f}M sales)", ha="center", fontsize=8)
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_ylim(0, reg["Margin %"].max() * 1.3)
ax.set_ylabel("Profit margin")
s_m = reg.loc["South", "Margin %"]
ax.set_title(f"South earns {s_m:.1f}% margin, about half the company's {margin:.1f}%")
save(fig, "q2_region")

# ---------------- 5. Q3: discount tiers with confidence intervals ----------------
disc = df.groupby("Discount Tier", observed=True).agg(
    lines=("Profit", "size"), sales=("Sales", "sum"), profit=("Profit", "sum"),
    mean_line_profit=("Profit", "mean"), sd=("Profit", "std"),
    loss_share_pct=("Profit", lambda p: (p < 0).mean() * 100))
disc["ci95"] = 1.96 * disc.sd / np.sqrt(disc.lines)
disc["margin_pct"] = disc.profit / disc.sales * 100
disc.drop(columns="sd").round(1).to_csv(ROOT / "discount_impact.csv")
plot = disc[disc.lines >= 30]
tiny = disc[disc.lines < 30]

fig, ax = plt.subplots(figsize=(8, 4.3))
ax.bar(plot.index.astype(str), plot.margin_pct, color=[DARK, DARK, ACCENT][: len(plot)])
for x, (m, n, s) in enumerate(zip(plot.margin_pct, plot.lines, plot.sales)):
    ax.text(x, m + 0.4, f"{m:.1f}%\nn = {n:,} lines", ha="center", fontsize=8)
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_ylim(0, plot.margin_pct.max() * 1.3)
ax.set_xlabel("Discount on the line")
ax.set_ylabel("Profit margin")
if len(tiny):
    ax.text(0.99, 0.97, f"Not shown: {int(tiny.lines.sum())} lines discounted >10% (too few to judge)",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.5, color=GREY)
d6, d15 = disc.loc["6-10%"], disc.loc["1-5%"]
ax.set_title(f"Lines discounted 6-10% earn {d6.margin_pct:.1f}% margin vs {d15.margin_pct:.1f}% at 1-5%")
save(fig, "q3_discount_impact")

# ---------------- 6. Q4: segments ----------------
seg = df.groupby("Customer Segment").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"),
                                         Customers=("Customer ID", "nunique"))
seg["Sales share %"] = (seg.Sales / seg.Sales.sum() * 100).round(1)
seg["Margin %"] = (seg.Profit / seg.Sales * 100).round(1)
seg = seg.sort_values("Sales", ascending=False)
seg.to_csv(ROOT / "segment_performance.csv")

fig, ax = plt.subplots(figsize=(8, 4.3))
ax.barh(seg.index[::-1], seg["Sales share %"][::-1], color=DARK)
for y, (sh, m) in enumerate(zip(seg["Sales share %"][::-1], seg["Margin %"][::-1])):
    ax.text(sh + 0.5, y, f"{sh:.1f}% of sales  |  {m:.1f}% margin", va="center", fontsize=8)
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_xlim(0, seg["Sales share %"].max() * 1.6)
ax.set_xlabel("Share of total sales")
top_seg = seg.index[0]
ax.set_title(f"{top_seg} is the largest segment ({seg.loc[top_seg, 'Sales share %']:.0f}% of sales); "
             f"margins range {seg['Margin %'].min():.0f}-{seg['Margin %'].max():.0f}%")
save(fig, "q4_segment")

# ---------------- 7. Q5: monthly sales with coverage gaps made visible ----------------
monthly.to_csv(ROOT / "monthly_trend.csv")
fig, ax = plt.subplots(figsize=(10, 4.3))
x = monthly.index.to_timestamp()
ax.bar(x, monthly.Sales.fillna(0) / 1e3, width=25, color=DARK)
for m in monthly.index[monthly.Sales.isna()]:
    ax.axvspan(m.to_timestamp(), (m + 1).to_timestamp(), color=ACCENT, alpha=0.25, lw=0)
ax.set_ylabel("Sales ($ thousands)")
low = int((monthly.Sales.fillna(0) < 10_000).sum())
ax.set_title(f"Uneven coverage: {low} of 48 months have under $10K of sales "
             f"({monthly.Sales.isna().sum()} have none, shaded)")
ax.text(0.01, 0.95, "Monthly sales swing more than 100x, with long near-empty stretches,\n"
        "so year-over-year growth and seasonality can't be read from this file.",
        transform=ax.transAxes, va="top", fontsize=8, color=GREY)
save(fig, "q5_monthly_trend")

# ---------------- 8. Save + print ----------------
kpi["discount_6_10_margin_pct"] = round(float(d6.margin_pct), 1)
kpi["discount_1_5_margin_pct"] = round(float(d15.margin_pct), 1)
kpi["discount_6_10_sales"] = int(d6.sales)
kpi["profit_if_6_10_tier_earned_1_5_margin"] = int(d6.sales * d15.margin_pct / 100 - d6.profit)
kpi["loss_making_subcategories"] = {k: int(v) for k, v in losers.Profit.items()}
kpi["south_profit_gap_vs_other_regions"] = int(south.gap.sum())
kpi["south_gap_top3"] = {k: int(v) for k, v in south.gap.nlargest(3).items()}
(ROOT / "kpi.json").write_text(json.dumps({"kpi": kpi, "data_audit": audit}, indent=2))
print(json.dumps({"kpi": kpi, "data_audit": audit}, indent=2))
print(disc.round(1).to_string())
print(cat.round(1).to_string())
print(seg.to_string())
