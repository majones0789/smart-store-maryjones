"""ETL: load prepared CSV data into the SQLite data warehouse.

Expected CSVs (under repo_root/data/prepared):
  - customers_data_prepared.csv
      CustomerID,Name,Region,JoinDate,LoyaltyPoints,PreferredContact
  - products_data_prepared.csv
      ProductID,ProductName,Category,UnitPrice,DiscountPercent,Supplier
  - sales_data_prepared.csv
      TransactionID,SaleDate,CustomerID,ProductID,StoreID,CampaignID,SaleAmount,DiscountPercent,PaymentType
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

from loguru import logger
import pandas as pd

from analytics_project.dw import DW_PATH, create_connection  # Local imports

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parents[3]  # .../smart-store-<user>
DATA_DIR: Path = REPO_ROOT / "data"
PREPARED_DIR: Path = DATA_DIR / "prepared"

CUSTOMERS_CSV: Path = PREPARED_DIR / "customers_data_prepared.csv"
PRODUCTS_CSV: Path = PREPARED_DIR / "products_data_prepared.csv"
SALES_CSV: Path = PREPARED_DIR / "sales_data_prepared.csv"

# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------


def _expect_file(path: Path, label: str) -> None:
    """Raise a crystal-clear error if a required file is missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found.\n"
            f"Expected at: {path.resolve()}\n"
            f"Tip: run ETL from the repo root and confirm filename matches exactly."
        )


def _percent_to_float(series: pd.Series) -> pd.Series:
    """Parse '10%' -> 0.10; numeric stays numeric; blanks become 0.0."""
    s = series.astype(str).str.strip()
    is_pct = s.str.endswith("%")
    out = pd.to_numeric(s.where(~is_pct), errors="coerce")
    out_pct = pd.to_numeric(s.where(is_pct).str.rstrip("%"), errors="coerce") / 100.0
    return out.fillna(out_pct).fillna(0.0)


def _money_to_float(series: pd.Series) -> pd.Series:
    """Parse monetary fields that might contain commas, spaces, or stray symbols."""
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip()
        .replace({"": None})
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )


def _iso_date(series: pd.Series) -> pd.Series:
    """Parse many date formats -> ISO 'YYYY-MM-DD' (NaT -> '')."""
    dt = pd.to_datetime(series, errors="coerce")
    return dt.dt.date.astype(str).where(dt.notna(), "")


# -----------------------------------------------------------------------------
# (Re)create tables
# -----------------------------------------------------------------------------

DDL = {
    "dim_customers": """
        CREATE TABLE IF NOT EXISTS dim_customers (
            customer_id      INTEGER PRIMARY KEY,
            customer_name    TEXT NOT NULL,
            region           TEXT NOT NULL,
            join_date        TEXT,          -- ISO date 'YYYY-MM-DD'
            loyalty_points   INTEGER DEFAULT 0,
            preferred_contact TEXT
        );
    """,
    "dim_products": """
        CREATE TABLE IF NOT EXISTS dim_products (
            product_id       INTEGER PRIMARY KEY,
            product_name     TEXT NOT NULL,
            category         TEXT NOT NULL,
            unit_price       REAL  NOT NULL,
            discount_percent REAL  NOT NULL,
            supplier         TEXT
        );
    """,
    "fact_sales": """
        CREATE TABLE IF NOT EXISTS fact_sales (
            transaction_id    INTEGER PRIMARY KEY,
            sale_date         TEXT,      -- ISO date
            customer_id       INTEGER,
            product_id        INTEGER,
            store_id          INTEGER,
            campaign_id       INTEGER,
            sale_amount       REAL,
            discount_percent  REAL,
            payment_type      TEXT,
            FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
            FOREIGN KEY (product_id)  REFERENCES dim_products(product_id)
        );
    """,
}


def create_tables(conn: sqlite3.Connection, drop_first: bool = True) -> None:
    """(Re)create the data warehouse tables in the SQLite database.

    Parameters
    ----------
    conn : sqlite3.Connection
        SQLite database connection.
    drop_first : bool, optional
        If True, drop existing tables before creating them (default is True).

    Returns
    -------
    None
    """
    cur = conn.cursor()
    if drop_first:
        cur.execute("DROP TABLE IF EXISTS fact_sales;")
        cur.execute("DROP TABLE IF EXISTS dim_products;")
        cur.execute("DROP TABLE IF EXISTS dim_customers;")
    for _name, sql in DDL.items():
        cur.execute(sql)
    conn.commit()
    logger.info("DW tables {} and recreated.", "dropped" if drop_first else "created")
    logger.info("DW tables {} and recreated.", "dropped" if drop_first else "created")


# -----------------------------------------------------------------------------
# Loaders
# -----------------------------------------------------------------------------
def load_dim_customers(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Load customer data from the prepared CSV into the dim_customers table.

    Parameters
    ----------
    conn : sqlite3.Connection
        SQLite database connection.

    Returns
    -------
    tuple[int, list[str]]
        Number of rows loaded and list of column names.
    """
    logger.info("Loading customers from {}", CUSTOMERS_CSV)
    _expect_file(CUSTOMERS_CSV, "Customers CSV")
    _expect_file(CUSTOMERS_CSV, "Customers CSV")

    df = pd.read_csv(CUSTOMERS_CSV)
    df = df.rename(
        columns={
            "CustomerID": "customer_id",
            "Name": "customer_name",
            "Region": "region",
            "JoinDate": "join_date",
            "LoyaltyPoints": "loyalty_points",
            "PreferredContact": "preferred_contact",
        }
    )

    # Clean
    df["join_date"] = _iso_date(df["join_date"])
    df["loyalty_points"] = (
        pd.to_numeric(df["loyalty_points"], errors="coerce").fillna(0).astype(int)
    )
    df = df.fillna({"customer_name": "", "region": "", "preferred_contact": ""})

    # Deduplicate on PK
    before = len(df)
    df = df.drop_duplicates(subset=["customer_id"], keep="first")
    dups = before - len(df)
    if dups:
        logger.warning("Dropped {} duplicate customer_id rows before load.", dups)

    df.to_sql("dim_customers", conn, if_exists="append", index=False)
    return len(df), df.columns.tolist()


def load_dim_products(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Load product data from the prepared CSV into the dim_products table.

    Parameters
    ----------
    conn : sqlite3.Connection
        SQLite database connection.

    Returns
    -------
    tuple[int, list[str]]
        Number of rows loaded and list of column names.
    """
    logger.info("Loading products from {}", PRODUCTS_CSV)
    _expect_file(PRODUCTS_CSV, "Products CSV")
    _expect_file(PRODUCTS_CSV, "Products CSV")

    df = pd.read_csv(PRODUCTS_CSV)
    df = df.rename(
        columns={
            "ProductID": "product_id",
            "ProductName": "product_name",
            "Category": "category",
            "UnitPrice": "unit_price",
            "DiscountPercent": "discount_percent",
            "Supplier": "supplier",
        }
    )

    # Clean
    df["unit_price"] = _money_to_float(df["unit_price"])
    df["discount_percent"] = _percent_to_float(df["discount_percent"])
    df = df.fillna({"product_name": "", "category": "", "supplier": ""})

    # Deduplicate on PK
    before = len(df)
    df = df.drop_duplicates(subset=["product_id"], keep="first")
    dups = before - len(df)
    if dups:
        logger.warning("Dropped {} duplicate product_id rows before load.", dups)

    df.to_sql("dim_products", conn, if_exists="append", index=False)
    return len(df), df.columns.tolist()


def load_fact_sales(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Load sales data from the prepared CSV into the fact_sales table.

    Parameters
    ----------
    conn : sqlite3.Connection
        SQLite database connection.

    Returns
    -------
    tuple[int, list[str]]
        Number of rows loaded and list of column names.
    """
    logger.info("Loading sales from {}", SALES_CSV)
    _expect_file(SALES_CSV, "Sales CSV")
    _expect_file(SALES_CSV, "Sales CSV")

    df = pd.read_csv(SALES_CSV)
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
    )

    # Clean/normalize
    df["sale_date"] = _iso_date(df["sale_date"])
    df["sale_amount"] = _money_to_float(df["sale_amount"])
    df["discount_percent"] = _percent_to_float(df["discount_percent"])
    df["payment_type"] = df["payment_type"].astype(str).str.strip().str.title()

    # Deduplicate on PK
    before = len(df)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")
    dups = before - len(df)
    if dups:
        logger.warning("Dropped {} duplicate transaction_id rows before load.", dups)

    df.to_sql("fact_sales", conn, if_exists="append", index=False)
    return len(df), df.columns.tolist()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main() -> None:
    """Run the ETL process to load prepared CSV data into the SQLite data warehouse."""
    logger.info("Starting DW ETL.")
    logger.info("Connecting to DW at {}", DW_PATH)

    conn = create_connection(DW_PATH)
    # ensure foreign keys enforce (SQLite default is OFF per-connection)
    conn.execute("PRAGMA foreign_keys = ON;")

    create_tables(conn, drop_first=True)

    cnt_c, cols_c = load_dim_customers(conn)
    logger.info("Loaded {} customers. Columns: {}", cnt_c, cols_c)

    cnt_p, cols_p = load_dim_products(conn)
    logger.info("Loaded {} products. Columns: {}", cnt_p, cols_p)

    cnt_s, cols_s = load_fact_sales(conn)
    logger.info("Loaded {} fact sales. Columns: {}", cnt_s, cols_s)

    logger.info("DW ETL complete.")


if __name__ == "__main__":
    main()
