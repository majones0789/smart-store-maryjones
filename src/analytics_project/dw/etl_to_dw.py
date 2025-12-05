# src/analytics_project/dw/etl_to_dw.py

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from analytics_project.dw import DW_PATH, create_connection


# ---------- Config ----------

REPO_ROOT = Path(__file__).resolve().parents[2]
PREPARED_DIR = REPO_ROOT / "data" / "prepared"

CUSTOMERS_CSV = PREPARED_DIR / "customers_data_prepared.csv"
PRODUCTS_CSV = PREPARED_DIR / "products_data_prepared.csv"
SALES_CSV = PREPARED_DIR / "sales_data_prepared.csv"


# ---------- Helpers ----------


def _drop_and_create_tables(cur) -> None:
    """Drop and recreate DW tables with a stable schema."""
    logger.info("DW tables dropped (if existed) and recreated.")

    cur.executescript(
        """
        DROP TABLE IF EXISTS dim_customers;
        DROP TABLE IF EXISTS dim_products;
        DROP TABLE IF EXISTS fact_sales;

        CREATE TABLE dim_customers (
            customer_id       INTEGER,
            customer_name     TEXT,
            region            TEXT,
            join_date         TEXT,   -- ISO date 'YYYY-MM-DD'
            loyalty_points    INTEGER,
            preferred_contact TEXT
        );

        CREATE TABLE dim_products (
            product_id        INTEGER,
            product_name      TEXT,
            category          TEXT,
            unit_price        REAL,
            discount_percent  REAL,
            supplier          TEXT
        );

        CREATE TABLE fact_sales (
            transaction_id    INTEGER,
            sale_date         TEXT,   -- ISO date
            customer_id       INTEGER,
            product_id        INTEGER,
            store_id          INTEGER,
            campaign_id       TEXT,
            sale_amount       REAL,
            discount_percent  REAL,
            payment_type      TEXT
        );
        """
    )


def _read_csv_expect(path: Path, expected_cols: tuple[str, ...]) -> pd.DataFrame:
    """Read a CSV and assert it has (at least) the expected columns."""
    df = pd.read_csv(path)
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}; found: {list(df.columns)}")
    return df


def _to_iso_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


# ---------- Loaders ----------


def _load_dim_customers(con) -> int:
    logger.info(f"Loading customers from {CUSTOMERS_CSV}")
    expected = ("CustomerID", "Name", "Region", "JoinDate", "LoyaltyPoints", "PreferredContact")
    df = _read_csv_expect(CUSTOMERS_CSV, expected)

    # Rename to DW schema; cast types
    df = df.rename(
        columns={
            "CustomerID": "customer_id",
            "Name": "customer_name",
            "Region": "region",
            "JoinDate": "join_date",
            "LoyaltyPoints": "loyalty_points",
            "PreferredContact": "preferred_contact",
        }
    ).copy()

    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    df["loyalty_points"] = pd.to_numeric(df["loyalty_points"], errors="coerce").astype("Int64")
    df["join_date"] = _to_iso_date(df["join_date"])

    df.to_sql("dim_customers", con, if_exists="append", index=False)
    logger.info(f"Loaded dim_customers: {len(df)} rows.")
    return len(df)


def _load_dim_products(con) -> int:
    logger.info(f"Loading products from {PRODUCTS_CSV}")
    expected = ("ProductID", "ProductName", "Category", "UnitPrice", "DiscountPercent", "Supplier")
    df = _read_csv_expect(PRODUCTS_CSV, expected)

    df = df.rename(
        columns={
            "ProductID": "product_id",
            "ProductName": "product_name",
            "Category": "category",
            "UnitPrice": "unit_price",
            "DiscountPercent": "discount_percent",
            "Supplier": "supplier",
        }
    ).copy()

    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce")

    df.to_sql("dim_products", con, if_exists="append", index=False)
    logger.info(f"Loaded dim_products: {len(df)} rows.")
    return len(df)


def _load_fact_sales(con) -> int:
    logger.info(f"Loading sales from {SALES_CSV}")
    expected = (
        "TransactionID",
        "SaleDate",
        "CustomerID",
        "ProductID",
        "StoreID",
        "CampaignID",
        "SaleAmount",
        "DiscountPercent",
        "PaymentType",
    )
    df = _read_csv_expect(SALES_CSV, expected)

    df = df.rename(
        columns={
            "TransactionID": "transaction_id",
            "SaleDate": "sale_date",
            "CustomerID": "customer_id",
            "ProductID": "product_id",
            "StoreID": "store_id",
            "CampaignID": "campaign_id",
            "SaleAmount": "sale_amount",
            "DiscountPercent": "discount_percent",
            "PaymentType": "payment_type",
        }
    ).copy()

    # Casts
    int_cols = ["transaction_id", "customer_id", "product_id", "store_id"]
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    df["sale_amount"] = pd.to_numeric(df["sale_amount"], errors="coerce")
    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce")
    df["sale_date"] = _to_iso_date(df["sale_date"])

    df.to_sql("fact_sales", con, if_exists="append", index=False)
    logger.info(f"Loaded fact_sales: {len(df)} rows.")
    return len(df)


# ---------- Main ----------


def main() -> None:
    logger.info("Starting DW ETL.")
    logger.info(f"Connecting to DW at {DW_PATH}")

    with create_connection(DW_PATH) as con:
        cur = con.cursor()
        _drop_and_create_tables(cur)

        n_customers = _load_dim_customers(con)
        n_products = _load_dim_products(con)
        n_sales = _load_fact_sales(con)

        con.commit()

    logger.info("DW ETL complete.")
    logger.info(f"Row counts -> customers: {n_customers}, products: {n_products}, sales: {n_sales}")


if __name__ == "__main__":
    main()
