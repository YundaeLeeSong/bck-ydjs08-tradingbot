"""
Alpaca package initialization.

Exposes the primary service for clean, top-level imports across the application.
"""

# [Facade] (1): Expose the domain service at the package root.
from .alpaca_service import AlpacaService

__all__ = [
    "AlpacaService",
]
