"""
Alphavi root package initialization.

Exposes the primary high-level data models and functional endpoints
for clean, top-level imports across the application.
"""

# [Facade] (1): Expose the domain models and endpoints at the package root.
from .models import StockDataDTO, StockDataTable
__all__ = [
    "StockDataDTO",
    "StockDataTable"
]
