"""ETL to load data into the data warehouse."""

from loguru import logger
import sqlite3
import pathlib
import csv


# ---------- Paths & Connections ----------


def get_project_root() -> pathlib.Path:
    """Return the project root folder (repo root)."""
    # etl_to_dw.py -> dw -> analytics_project -> src -> REPO
    return pathlib.Path(__file__).resolve().parents[3]


def get_db_path() -> pathlib.Path:
    """Return the path to the data warehouse SQLite file."""
    project_root = get_project_root()
    db_path = project_root / "data" / "smart_store_dw.db"
    return db_path


def create_connection(db_path: pathlib.Path) -> sqlite3.Connection:
    """Create a SQLite connection to the DW database."""
    logger.info(f"Connecting to DW at {db_path}")
    conn = sqlite3.connect(db_path)
    return conn


# ---------- Schema Creation ----------


def create_tables(conn: sqlite3.Connection) -> None:
    """Drop and recreate DW tables for customers, products, and sales."""
    cursor = conn.cursor()

    # Drop fact table first (because of foreign keys), then dimensions
    cursor.execute("DROP TABLE IF EXISTS fact_sales;")
    cursor.execute("DROP TABLE IF EXISTS dim_products;")
    cursor.execute("DROP TABLE IF EXISTS dim_customers;")

    sql_dim_customers = """
    CREATE TABLE dim_customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT,
        region TEXT,
        join_date TEXT,
        loyalty_points INTEGER,
        preferred_contact TEXT
    );
    """

    sql_dim_products = """
    CREATE TABLE dim_products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        unit_price REAL,
        discount_percent REAL,
        supplier TEXT
    );
    """

    sql_fact_sales = """
    CREATE TABLE fact_sales (
        transaction_id INTEGER PRIMARY KEY,
        sale_date TEXT,
        customer_id INTEGER,
        product_id INTEGER,
        store_id INTEGER,
        campaign_id INTEGER,
        sale_amount REAL,
        discount_percent REAL,
        payment_type TEXT,
        FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
        FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
    );
    """

    cursor.execute(sql_dim_customers)
    cursor.execute(sql_dim_products)
    cursor.execute(sql_fact_sales)

    conn.commit()
    logger.info("DW tables dropped (if existed) and recreated.")


# ---------- Load Dimension Tables ----------


def load_dim_customers(conn: sqlite3.Connection, csv_path: pathlib.Path) -> None:
    """Load prepared customer data into dim_customers."""
    logger.info(f"Loading customers from {csv_path}")

    cursor = conn.cursor()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        logger.info(f"Customer CSV headers: {reader.fieldnames}")

        for row in reader:
            cursor.execute(
                """
                INSERT OR REPLACE INTO dim_customers (
                    customer_id,
                    customer_name,
                    region,
                    join_date,
                    loyalty_points,
                    preferred_contact
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["CustomerID"],
                    row["Name"],
                    row["Region"],
                    row["JoinDate"],
                    row["LoyaltyPoints"],
                    row["PreferredContact"],
                ),
            )

    conn.commit()
    logger.info("Loaded dim_customers.")


def load_dim_products(conn: sqlite3.Connection, csv_path: pathlib.Path) -> None:
    """Load prepared product data into dim_products."""
    logger.info(f"Loading products from {csv_path}")

    cursor = conn.cursor()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        logger.info(f"Product CSV headers: {reader.fieldnames}")

        for row in reader:
            cursor.execute(
                """
                INSERT OR REPLACE INTO dim_products (
                    product_id,
                    product_name,
                    category,
                    unit_price,
                    discount_percent,
                    supplier
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["ProductID"],
                    row["ProductName"],
                    row["Category"],
                    row["UnitPrice"],
                    row["DiscountPercent"],
                    row["Supplier"],
                ),
            )

    conn.commit()
    logger.info("Loaded dim_products.")


# ---------- Load Fact Table ----------


def load_fact_sales(conn: sqlite3.Connection, csv_path: pathlib.Path) -> None:
    """Load prepared sales data into fact_sales."""
    logger.info(f"Loading sales from {csv_path}")

    cursor = conn.cursor()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        logger.info(f"Sales CSV headers: {reader.fieldnames}")

        for row in reader:
            cursor.execute(
                """
                INSERT OR REPLACE INTO fact_sales (
                    transaction_id,
                    sale_date,
                    customer_id,
                    product_id,
                    store_id,
                    campaign_id,
                    sale_amount,
                    discount_percent,
                    payment_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["TransactionID"],
                    row["SaleDate"],
                    row["CustomerID"],
                    row["ProductID"],
                    row["StoreID"],
                    row["CampaignID"],
                    row["SaleAmount"],
                    row["DiscountPercent"],
                    row["PaymentType"],
                ),
            )

    conn.commit()
    logger.info("Loaded fact_sales.")


# ---------- Main ETL ----------


def main() -> None:
    """Main ETL entry point to create and populate the DW."""
    logger.info("Starting DW ETL.")

    db_path = get_db_path()
    conn = create_connection(db_path)

    try:
        # Recreate tables every time
        create_tables(conn)

        # Paths to prepared data
        project_root = get_project_root()
        prepared_dir = project_root / "data" / "prepared"

        customers_csv = prepared_dir / "customers_data_prepared.csv"
        products_csv = prepared_dir / "products_data_prepared.csv"
        sales_csv = prepared_dir / "sales_data_prepared.csv"

        logger.info(f"Using prepared data from {prepared_dir}")

        # Load tables
        load_dim_customers(conn, customers_csv)
        load_dim_products(conn, products_csv)
        load_fact_sales(conn, sales_csv)
    finally:
        conn.close()
        logger.info("DW ETL complete.")


if __name__ == "__main__":
    main()
    print("ETL finished running.")
    logger.info("ETL finished running.")
