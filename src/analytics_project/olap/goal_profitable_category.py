"""P6: BI Insights & Storytelling.

Goal: Identify the most profitable (net sales) product category in the last 12 months,
overall and by region, with a monthly trend (drilldown to month).

This script will:
- Load data from DW if available, otherwise from prepared CSVs
- Build net sales metrics (handles discount)
- Slice to the last 12 months of sales
- Dice by category and region
- Drilldown: month-level trend for top categories
- Save a summary CSV and a couple of charts to /src/data/olap_outputs
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd

# ----------------------------
# Paths
# ----------------------------
ROOT = Path()
DATA_PREP = ROOT / "data" / "prepared"
DB_PATH = ROOT / "data" / "smart_store_dw.db"
OUTDIR = ROOT / "src" / "data" / "olap_outputs"
OUTDIR.mkdir(parents=True, exist_ok=True)

CUSTOMERS_CSV = DATA_PREP / "customers_data_prepared.csv"
PRODUCTS_CSV = DATA_PREP / "products_data_prepared.csv"
SALES_CSV = DATA_PREP / "sales_data_prepared.csv"


# ----------------------------
# Load helpers
# ----------------------------
def _load_from_dw() -> pd.DataFrame | None:
    """Try to read a joined view from the DW. Return None if unavailable."""
    if not DB_PATH.exists():
        return None
    con = sqlite3.connect(DB_PATH)
    try:
        # Expecting P4/P5 tables; adapt names if yours differ
        q = """
        SELECT
            fs.TransactionID      AS transaction_id,
            fs.SaleDate           AS sale_date,
            fs.CustomerID         AS customer_id,
            fs.ProductID          AS product_id,
            fs.SaleAmount         AS sale_amount,
            fs.DiscountPercent    AS discount_percent,
            c.Region              AS region,
            p.Category            AS category
        FROM fact_sales fs
        JOIN dim_customers c ON c.customer_id = fs.CustomerID
        JOIN dim_products  p ON p.product_id  = fs.ProductID
        """
        return pd.read_sql(q, con)
    except Exception:
        return None
    finally:
        con.close()


def _load_from_prepared() -> pd.DataFrame:
    """Join prepared CSVs (customers/products/sales) into one analysis frame."""
    cust = pd.read_csv(CUSTOMERS_CSV)
    prod = pd.read_csv(PRODUCTS_CSV)
    sale = pd.read_csv(SALES_CSV)

    # Standardize column names (based on your screenshots)
    cust.columns = [
        "customer_id",
        "customer_name",
        "region",
        "join_date",
        "loyalty_points",
        "preferred_contact",
    ]
    prod.columns = [
        "product_id",
        "product_name",
        "category",
        "unit_price",
        "discount_percent_prod",
        "supplier",
    ]
    sale.columns = [
        "transaction_id",
        "sale_date",
        "customer_id",
        "product_id",
        "store_id",
        "campaign_id",
        "sale_amount",
        "discount_percent",
        "payment_type",
    ]

    return sale.merge(cust[["customer_id", "region"]], on="customer_id", how="left").merge(
        prod[["product_id", "category"]], on="product_id", how="left"
    )


def load_sales_joined() -> pd.DataFrame:
    """Load and join sales, customer, and product data from the data warehouse or prepared CSVs.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing joined sales, customer, and product information with cleaned types.
    """
    df = _load_from_dw()
    if df is None:
        df = _load_from_prepared()
    # Clean types
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")
    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce").fillna(0)
    df["sale_amount"] = pd.to_numeric(df["sale_amount"], errors="coerce").fillna(0)
    df["region"] = df["region"].fillna("Unknown")
    df["category"] = df["category"].fillna("Unknown")
    return df.dropna(subset=["sale_date"])


# ----------------------------
# OLAP transforms
# ----------------------------
def slice_last_12_months(df: pd.DataFrame) -> pd.DataFrame:
    """Slice the DataFrame to include only sales from the last 12 months.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing a 'sale_date' column.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with sales from the last 12 months.
    """
    max_date = df["sale_date"].max()
    if pd.isna(max_date):
        return df.iloc[0:0].copy()
    cutoff = max_date - pd.DateOffset(years=1)
    return df.loc[df["sale_date"] > cutoff].copy()


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add calculated metrics to the DataFrame, including net sales and month.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing sales data with 'sale_amount', 'discount_percent', and 'sale_date' columns.

    Returns
    -------
    pd.DataFrame
        DataFrame with additional 'net_sales' and 'month' columns.
    """
    df = df.copy()
    df["net_sales"] = df["sale_amount"] * (1 - (df["discount_percent"] / 100.0))
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["month"] = df["sale_date"].dt.to_period("M").dt.to_timestamp()  # type: ignore
    return df


def summarize_by_category_region(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize net sales and order counts by product category and region.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing sales data with 'category', 'region', 'net_sales', and 'transaction_id' columns.

    Returns
    -------
    pd.DataFrame
        Aggregated DataFrame with net sales and order counts by category and region.
    """
    agg = df.groupby(["category", "region"], as_index=False).agg(
        Net_Sales=("net_sales", "sum"), Orders=("transaction_id", "count")
    )
    agg["Net_Sales"] = agg["Net_Sales"].round(2)
    return agg.sort_values(["Net_Sales"], ascending=False)


def monthly_trend_for_top_categories(df: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
    """Generate monthly net sales trend for the top product categories.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing sales data with 'category', 'month', 'net_sales', and 'transaction_id' columns.
    top_k : int, default=3
        Number of top categories to include in the trend analysis.

    Returns
    -------
    pd.DataFrame
        DataFrame with monthly net sales and order counts for the top categories.
    """
    by_cat = (
        df.groupby("category", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )  # type: ignore
    top = set(by_cat.head(top_k)["category"])
    trend = (
        df[df["category"].isin(top)]
        .groupby(["month", "category"], as_index=False)
        .agg(Net_Sales=("net_sales", "sum"), Orders=("transaction_id", "count"))
    )
    trend["Net_Sales"] = trend["Net_Sales"].round(2)
    return trend.sort_values(["month", "Net_Sales"], ascending=[True, False])


# ----------------------------
# Visualization helpers
# ----------------------------
def chart_category_region_bar(summary: pd.DataFrame, out_png: Path):
    """Create a bar chart showing net sales by category and region.

    Parameters
    ----------
    summary : pd.DataFrame
        DataFrame containing 'category', 'region', and 'Net_Sales' columns.
    out_png : Path
        Output path for saving the chart as a PNG file.
    """
    # Pivot to categories x regions
    piv = summary.pivot(index="category", columns="region", values="Net_Sales").fillna(0)
    ax = piv.plot(kind="bar", figsize=(10, 6))
    ax.set_title("Net Sales by Category and Region (Last 12 Months)")
    ax.set_ylabel("Net Sales (USD)")
    ax.set_xlabel("Category")
    ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


def chart_monthly_trend(trend: pd.DataFrame, out_png: Path):
    """Create a line chart showing monthly net sales trend for top categories.

    Parameters
    ----------
    trend : pd.DataFrame
        DataFrame containing 'month', 'category', and 'Net_Sales' columns.
    out_png : Path
        Output path for saving the chart as a PNG file.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    for cat, sub in trend.groupby("category"):
        ax.plot(sub["month"], sub["Net_Sales"], marker="o", label=cat)
    ax.set_title("Monthly Net Sales Trend (Top Categories)")
    ax.set_ylabel("Net Sales (USD)")
    ax.set_xlabel("Month")
    ax.legend(title="Category", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


# ----------------------------
# Main
# ----------------------------
def main():
    """Execute the OLAP analysis to identify the most profitable product category.

    This function loads sales data, slices it to the last 12 months, calculates metrics,
    summarizes by category and region, generates monthly trends for top categories,
    and saves outputs including CSV summaries and visualizations.
    """
    print("P6 OLAP: Loading data...")
    df = load_sales_joined()
    if df.empty:
        print("No data available.")
        return

    print("Slicing: last 12 months")
    df = slice_last_12_months(df)
    df = add_metrics(df)

    print("Summarizing by category and region...")
    summary = summarize_by_category_region(df)
    summary_path = OUTDIR / "p6_category_region_summary.csv"
    summary.to_csv(summary_path, index=False)

    print("Building monthly trend for top categories...")
    trend = monthly_trend_for_top_categories(df, top_k=3)
    trend_path = OUTDIR / "p6_monthly_trend_top_categories.csv"
    trend.to_csv(trend_path, index=False)

    # Charts
    chart_category_region_bar(summary, OUTDIR / "p6_category_region_bar.png")
    chart_monthly_trend(trend, OUTDIR / "p6_top_categories_monthly_trend.png")

    # Console highlight: best category overall
    best = (
        summary.groupby("category", as_index=False)["Net_Sales"]
        .sum()
        .sort_values("Net_Sales", ascending=False)  # type: ignore
        .head(1)
    )  # type: ignore
    best_cat = best.iloc[0]["category"]
    best_val = best.iloc[0]["Net_Sales"]
    print(f"✅ Most profitable category (last 12 months): {best_cat} (${best_val:,.2f})")

    print("\nOutputs:")
    print(f" - {summary_path}")
    print(f" - {trend_path}")
    print(f" - {OUTDIR / 'p6_category_region_bar.png'}")
    print(f" - {OUTDIR / 'p6_top_categories_monthly_trend.png'}")


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    print("✅ OLAP analysis completed successfully!")
