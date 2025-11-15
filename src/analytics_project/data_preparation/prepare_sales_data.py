from pathlib import Path
import pandas as pd

# Import the reusable scrubber + logger
from src.analytics_project.data_scrubber import DataScrubber
from src.analytics_project.utils_logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    # ---------------------------------------------------------
    # Project root (folder ABOVE "data")
    # ---------------------------------------------------------
    project_root = Path(__file__).resolve().parents[2]

    # File paths
    input_file = project_root / "data" / "raw" / "sales_data.csv"
    output_file = project_root / "data" / "prepared" / "sales_data_prepared.csv"

    logger.info(f"Reading raw sales data from: {input_file}")

    # Load the CSV
    df = pd.read_csv(input_file)
    original_shape = df.shape

    # ---------------------------------------------------------
    # Run the reusable cleaning pipeline
    # ------------
