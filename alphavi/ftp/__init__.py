"""
FTP (Financial Modeling Prep) package initialization.

Exposes the core FMPService class for clean, top-level imports.
"""

# [Facade] (1): Expose the underlying API service to the rest of the application.
from .fmp_service import FMPService

__all__ = ["FMPService"]
