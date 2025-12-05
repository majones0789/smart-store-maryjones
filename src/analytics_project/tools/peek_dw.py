"""Peek into the data warehouse to summarize table row counts and date ranges.

This script connects to the smart_store_dw.db SQLite database and prints summary information
about allowed tables, including row counts, column names, and the date range for sales.
"""

# src/analytics_project/tools/peek_dw.py
import json
import pathlib
import sqlite3

# Point to your DW file
db = pathlib.Path(r"src/data/smart_store_dw.db")
con = sqlite3.connect(db)
cur = con.cursor()


def cols(table: str):
    """Return column names for a given table."""
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


info = {}
allowed_tables = {"fact_sales", "dim_customers", "dim_products"}
for t in allowed_tables:
    # Only use table names from the allowed_tables set to prevent SQL injection
    if t in allowed_tables:
        cnt = cur.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]  # noqa: Q003, S608
        info[t] = {"rows": cnt, "cols": cols(t)}

mn, mx = cur.execute("SELECT MIN(date(sale_date)), MAX(date(sale_date)) FROM fact_sales").fetchone()
info["fact_sales_date_range"] = {"min": mn, "max": mx}

print(json.dumps(info, indent=2))
con.close()
