# src/analytics_project/__init__.py
# Make analytics_project a regular package (not a namespace package).

# Re-export safe helpers
from .dw import DW_PATH, create_connection

__all__ = ["DW_PATH", "create_connection"]
