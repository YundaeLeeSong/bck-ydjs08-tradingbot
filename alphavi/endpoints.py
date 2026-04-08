"""
API endpoints and data orchestrators for the alphavi project.

Provides high-level functional endpoints to easily fetch, patch, and construct
market data models from external data sources.
"""

from typing import List
from alphavi.models import StockDataTable
# [Facade] (2): Consume the internal service via the clean, exposed interface.
from alphavi.ftp import FMPService

def load_market_data(tickers: List[str]) -> StockDataTable:
    """
    Creates a new StockDataTable and populates it with data for the given tickers.
    
    Args:
        tickers (List[str]): A list of stock symbols (e.g., ['AAPL', 'TSLA']).
        
    Returns:
        StockDataTable: A newly created table populated with the fetched DTOs.
    """
    # Validate input list
    if not tickers or not isinstance(tickers, list):
        return StockDataTable()

    table = StockDataTable()
    patch_market_data(table, tickers)
    return table

def patch_market_data(table: StockDataTable, tickers: List[str]) -> None:
    """
    Updates an existing StockDataTable with data for the given tickers.
    
    Args:
        table (StockDataTable): The table to update.
        tickers (List[str]): A list of stock symbols (e.g., ['AAPL', 'TSLA']).
    """
    # Validate input objects
    if not table or not isinstance(table, StockDataTable):
        return
    if not tickers or not isinstance(tickers, list):
        return

    api_service = FMPService()
    for ticker in tickers:
        dto = api_service.get_stock_data(ticker)
        if dto:
            table.add(dto)
