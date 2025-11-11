"""
scripts/data_preparation/prepare_sales.py

This script reads sales data from the data/raw folder, cleans the data,
and writes the cleaned version to the data/prepared folder.
"""

#####################################
# Import Modules at the Top
#####################################

import pathlib
import pandas as pd
from analytics_project.utils_logger import logger

#####################################
# Path Constants
#####################################

# __file__ = .../src/analytics_project/data_preparation/prepare_sales_data.py
# parents[0] = .../src/analytics_project/data_preparation
# parents[1] = .../src/analytics_project
# parents[2] = .../src
# parents[3] = .../smart-store-maryjones  ← project root
PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[3]

DATA_DIR: pathlib.Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: pathlib.Path = DATA_DIR / "raw"
PREPARED_DATA_DIR: pathlib.Path = DATA_DIR / "prepared"

DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
PREPARED_DATA_DIR.mkdir(exist_ok=True)

#####################################
# Helper Functions
#####################################

def read_raw_data(file_name: str) -> pd.DataFrame:
    file_path: pathlib.Path = RAW_DATA_DIR / file_name
    try:
        logger.info(f"READING: {file_path}.")
        return pd.read_csv(file_path)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()


def save_prepared_data(df: pd.DataFrame, file_name: str) -> None:
    logger.info(
        f"FUNCTION START: save_prepared_data with file_name={file_name}, dataframe shape={df.shape}"
    )
    file_path = PREPARED_DATA_DIR / file_name
    df.to_csv(file_path, index=False)
    logger.info(f"Data saved to {file_path}")


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"FUNCTION START: remove_duplicates with dataframe shape={df.shape}")
    before = df.shape[0]
    df_deduped = df.drop_duplicates()
    after = df_deduped.shape[0]
    logger.info(f"Original rows: {before}, deduped rows: {after}, removed {before - after}")
    return df_deduped


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"FUNCTION START: handle_missing_values with dataframe shape={df.shape}")
    missing_before = df.isna().sum().sum()
    logger.info(f"Total missing values before handling: {missing_before}")
    # TODO: add real rules if you want (e.g. drop rows with missing key IDs)
    missing_after = df.isna().sum().sum()
    logger.info(f"Total missing values after handling: {missing_after}")
    logger.info(f"{len(df)} records remaining after handling missing values.")
    return df


def remove_outliers(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"FUNCTION START: remove_outliers with dataframe shape={df.shape}")
    initial_count = len(df)
    # TODO: add real rules if you want (e.g. filter impossible quantities or prices)
    removed_count = initial_count - len(df)
    logger.info(f"Removed {removed_count} outlier rows")
    logger.info(f"{len(df)} records remaining after removing outliers.")
    return df


#####################################
# Main
#####################################

def main() -> None:
    logger.info("==================================")
    logger.info("STARTING prepare_sales_data.py")
    logger.info("==================================")

    logger.info(f"PROJECT ROOT : {PROJECT_ROOT}")
    logger.info(f"data/raw     : {RAW_DATA_DIR}")
    logger.info(f"data/prepared: {PREPARED_DATA_DIR}")

    input_file = "sales_data.csv"
    output_file = "sales_data_prepared.csv"

    df = read_raw_data(input_file)

    if df.empty:
        logger.error("No data loaded – aborting cleaning.")
        return

    original_shape = df.shape
    logger.info(f"Initial dataframe columns: {', '.join(df.columns.tolist())}")
    logger.info(f"Initial dataframe shape: {df.shape}")

    original_columns = df.columns.tolist()
    df.columns = df.columns.str.strip()
    changed_columns = [
        f"{old} -> {new}" for old, new in zip(original_columns, df.columns) if old != new
    ]
    if changed_columns:
        logger.info(f"Cleaned column names: {', '.join(changed_columns)}")

    df = remove_duplicates(df)
    df = handle_missing_values(df)
    df = remove_outliers(df)

    save_prepared_data(df, output_file)

    cleaned_shape = df.shape
    logger.info("==================================")
    logger.info(f"Original shape: {original_shape}")
    logger.info(f"Cleaned shape:  {cleaned_shape}")
    logger.info("==================================")
    logger.info("FINISHED prepare_sales_data.py")
    logger.info("==================================")


if __name__ == "__main__":
    main()
