from pathlib import Path
import sqlite3

# repo root -> /your-repo
REPO_ROOT = Path(__file__).resolve().parents[2]
DW_PATH = REPO_ROOT / "data" / "smart_store_dw.db"


def create_connection(path: Path) -> sqlite3.Connection:
    """Create a connection to the SQLite database.

    Parameters
    ----------
    path : Path
        Path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        A connection object to the SQLite database.
    """
    return sqlite3.connect(path)
