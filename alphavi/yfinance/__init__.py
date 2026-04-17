"""
YFinance package initialization.

Exposes the core YFinanceService class for clean, top-level imports.
"""

# [Facade] (1): Expose the underlying API service to the rest of the application.
from .yfinance_service import YFinanceService

__all__ = ["YFinanceService"]
