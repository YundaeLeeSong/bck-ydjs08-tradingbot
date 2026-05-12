"""
External Services Interface
===========================

This module consolidates external third-party API clients used by the trading bot.
It exposes the primary service classes for Alpaca (brokerage), FMP (fundamentals), 
and Yahoo Finance (market data/analysis), allowing for clean, top-level imports 
across the application.

Example:
    from bumblebee.external import AlpacaService, FMPService, YFinanceService
"""

from .alpaca_service import AlpacaService
from .fmp_service import FMPService
from .yfinance_service import YFinanceService
from .gmail_service import GmailService

__all__ = [
    "AlpacaService",
    "FMPService",
    "YFinanceService",
    "GmailService",
]
