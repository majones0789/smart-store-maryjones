"""
scripts/data_preparation/prepare_customers.py

This script reads customer data from the data/raw folder, cleans the data,
and writes the cleaned version to the data/prepared folder.

Tasks:
- Remove duplicates
- Handle missing values
- Remove outliers
- Ensure consistent formatting
"""

#####################################
# Import Modules at the Top
#####################################

# Import from Python Standard Library
import pathlib

# Import from external packages (requires a virtual environment)
import pandas as pd

# Import local modules (use your actual logger module)
from analytics_project.utils_logger import logger


#####################################
# Path Constants
#####################################

# __file__ = .../src/analytics_project/data_preparation/prepare_customers_data.py
# parents[0] = .../src/analytics_project/data_preparation
# parents[1] = .../src/analytics_project
# parents[2] = .../src
# parents[3] = .../smart-store-maryjones  ← project root
PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[3]

DATA_DIR: pathlib.Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: pathlib.Path = DATA_DIR / "raw"
PREPARED_DATA_DIR: pathlib.Path = DATA_DIR / "prepared"

# Ensure the directories exist or create them
DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
PREPARED_DATA_DIR.mkdir(exist_ok=True)


#####################################
# Define Functions - Reusable blocks of code / instructions
#####################################

def read_raw_data(file_name: str) -> pd.DataFrame:
    """Read raw data from CSV."""
    file_path: pathlib.Path = RAW_DATA_DIR / file_name
    try:
        logger.info(f"READING: {file_path}.")
        return pd.read_csv(file_path)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return pd.DataFrame()  # Return an empty DataFrame if the file is not found
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if any other error occurs


def save_prepared_data(df: pd.DataFrame, file_name: str) -> None:
    """
    Save cleaned data to CSV.

    Args:
        df (pd.DataFrame): Cleaned DataFrame.
        file_name (str): Name of the output file.
    """
    logger.info(
        f"FUNCTION START: save_prepared_data with file_name={file_name}, dataframe shape={df.shape}"
    )
    file_path = PREPARED_DATA_DIR / file_name
    df.to_csv(file_path, index=False)
    logger.info(f"Data saved to {file_path}")


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate rows from the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: DataFrame with duplicates removed.
    """
    logger.info(f"FUNCTION START: remove_duplicates with dataframe shape={df.shape}")

    before = df.shape[0]
    df_deduped = df.drop_duplicates()
    after = df_deduped.shape[0]

    logger.info(f"Original dataframe rows: {before}")
    logger.info(f"Deduped dataframe rows:  {after}")
    logger.info(f"Removed {before - after} duplicate rows.")
    return df_deduped


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values by filling or dropping.
    This logic is specific to the actual data and business rules.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: DataFrame with missing values handled.
    """
    logger.info(f"FUNCTION START: handle_missing_values with dataframe shape={df.shape}")

    # Log missing values count before handling
    missing_before = df.isna().sum().sum()
    logger.info(f"Total missing values before handling: {missing_before}")

    # TODO: Fill or drop missing values based on business rules
    # Example:
    # df['CustomerName'].fillna('Unknown', inplace=True)
    # df.dropna(subset=['CustomerID'], inplace=True)

    # Log missing values count after handling
    missing_after = df.isna().sum().sum()
    logger.info(f"Total missing values after handling: {missing_after}")
    logger.info(f"{len(df)} records remaining after handling missing values.")
    return df


def remove_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove outliers based on thresholds.
    This logic is very specific to the actual data and business rules.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: DataFrame with outliers removed.
    """
    logger.info(f"FUNCTION START: remove_outliers with dataframe shape={df.shape}")
    initial_count = len(df)

    # TODO: Define numeric columns and apply rules for outlier removal
    # Example:
    # df = df[(df['Age'] > 18) & (df['Age'] < 100)]

    removed_count = initial_count - len(df)
    logger.info(f"Removed {removed_count} outlier rows")
    logger.info(f"{len(df)} records remaining after removing outliers.")
    return df


#####################################
# Define Main Function - The main entry point of the script
#####################################

def main() -> None:
    """
    Main function for processing customer data.
    """
    logger.info("==================================")
    logger.info("STARTING prepare_customers_data.py")
    logger.info("==================================")

    logger.info(f"PROJECT ROOT : {PROJECT_ROOT}")
    logger.info(f"data/raw     : {RAW_DATA_DIR}")
    logger.info(f"data/prepared: {PREPARED_DATA_DIR}")

    # Match the assignment naming: customers_data_prepared.csv
    input_file = "customers_data.csv"
    output_file = "customers_data_prepared.csv"

    # Read raw data
    df = read_raw_data(input_file)

    # If nothing loaded, stop early so we don't crash on empty data
    if df.empty:
        logger.error("No data loaded – aborting cleaning.")
        return

    # Record original shape
    original_shape = df.shape

    # Log initial dataframe information
    logger.info(f"Initial dataframe columns: {', '.join(df.columns.tolist())}")
    logger.info(f"Initial dataframe shape: {df.shape}")

    # Clean column names
    original_columns = df.columns.tolist()
    df.columns = df.columns.str.strip()

    # Log if any column names changed
    changed_columns = [
        f"{old} -> {new}" for old, new in zip(original_columns, df.columns) if old != new
    ]
    if changed_columns:
        logger.info(f"Cleaned column names: {', '.join(changed_columns)}")

    # Remove duplicates
    df = remove_duplicates(df)

    # Handle missing values
    df = handle_missing_values(df)

    # Remove outliers
    df = remove_outliers(df)

    # Save prepared data
    save_prepared_data(df, output_file)

    cleaned_shape = df.shape

    logger.info("==================================")
    logger.info(f"Original shape: {original_shape}")
    logger.info(f"Cleaned shape:  {cleaned_shape}")
    logger.info("==================================")
    logger.info("FINISHED prepare_customers_data.py")
    logger.info("==================================")


#####################################
# Conditional Execution Block
#####################################

if __name__ == "__main__":
    main()
