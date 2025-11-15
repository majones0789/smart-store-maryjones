import pandas as pd
import numpy as np

class DataScrubber:
    """Reusable class for common data cleaning steps."""

    def __init__(self):
        print("DataScrubber initialized!")

    # -------------------------------------------------------
    # REMOVE DUPLICATES
    # -------------------------------------------------------
    def remove_duplicates(self, df):
        """Remove duplicate rows from a DataFrame."""
        before = len(df)
        df = df.drop_duplicates()
        after = len(df)
        print(f"Removed {before - after} duplicates.")
        return df

    # -------------------------------------------------------
    # STANDARDIZE COLUMN NAMES
    # -------------------------------------------------------
    def standardize_columns(self, df):
        """
        Convert column names to lowercase, remove spaces,
        and replace them with underscores.
        """
        original = df.columns.tolist()
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        print(f"Standardized columns: {original} -> {df.columns.tolist()}")
        return df

    # -------------------------------------------------------
    # HANDLE MISSING VALUES
    # -------------------------------------------------------
    def handle_missing(self, df, strategy="smart"):
        """
        Handle missing values.

        strategy options:
        - 'smart' : fill numeric columns with median and text columns with mode
        - 'drop'  : remove rows with any missing values
        - 'none'  : do nothing
        """
        df = df.copy()

        if strategy == "none":
            print("No missing value handling applied.")
            return df

        if strategy == "drop":
            before = len(df)
            df = df.dropna()
            after = len(df)
            print(f"Dropped {before - after} rows with missing values.")
            return df

        # ---- SMART FILL ----
        num_cols = df.select_dtypes(include=["number"]).columns
        cat_cols = df.select_dtypes(exclude=["number"]).columns

        # Fill numeric columns with median
        for col in num_cols:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)

        # Fill categorical columns with mode (or "Unknown" if mode unavailable)
        for col in cat_cols:
            mode_series = df[col].mode()
            fill_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            df[col] = df[col].fillna(fill_val)

        print("Filled missing numeric values with median and categorical values with mode.")
        return df

    # -------------------------------------------------------
    # REMOVE OUTLIERS WITH IQR METHOD
    # -------------------------------------------------------
    def remove_outliers_iqr(self, df, cols, k=1.5):
        """
        Remove outliers for specified numeric columns using IQR.
        Rows outside [Q1 - k*IQR, Q3 + k*IQR] are removed.

        cols: list of columns to check
        k: IQR multiplier (1.5 = typical, 3.0 = conservative)
        """
        df = df.copy()

        if not cols:
            print("No outlier columns provided.")
            return df

        mask = pd.Series(True, index=df.index)

        for c in cols:
            if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                q1 = df[c].quantile(0.25)
                q3 = df[c].quantile(0.75)
                iqr = q3 - q1
                low = q1 - k * iqr
                high = q3 + k * iqr

                # keep rows in the allowed range
                mask &= df[c].between(low, high) | df[c].isna()

        before = len(df)
        df = df[mask]
        after = len(df)
        print(f"Removed {before - after} outliers from columns {cols} (k={k}).")

        return df
    # -------------------------------------------------------
    # STANDARD PIPELINE (DUPES → COLS → MISSING → OUTLIERS)
    # -------------------------------------------------------
    def run_standard_pipeline(
        self,
        df,
        outlier_cols=None,
        missing_strategy="smart",
        k=1.5,
        drop_duplicates=True,
    ):
        """
        Run a standard cleaning pipeline on a DataFrame.

        Steps:
        1. Optionally remove duplicate rows
        2. Standardize column names
        3. Handle missing values
        4. Optionally remove outliers on selected numeric columns
        """
        df = df.copy()

        if drop_duplicates:
            df = self.remove_duplicates(df)

        df = self.standardize_columns(df)
        df = self.handle_missing(df, strategy=missing_strategy)

        if outlier_cols:
            df = self.remove_outliers_iqr(df, cols=outlier_cols, k=k)

        return df
