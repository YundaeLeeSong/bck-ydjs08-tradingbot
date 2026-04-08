"""
Data transfer objects and models for the alphavi project.

This module defines the primary data structures used to hold and organize
financial stock data, including individual DTOs and aggregated tables.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class StockDataDTO:
    """
    A Data Transfer Object representing a comprehensive set of financial metrics
    for a single stock symbol.
    """
    symbol: str = ""
    name: str = ""
    industry: str = ""
    sector: str = ""
    price: float = 0.0
    latestChangePercent: float = 0.0
    
    # 1. Profile
    marketCap: float = 0.0
    beta: float = 0.0
    volume: int = 0
    averageVolume: int = 0
    
    # 2. Ratios
    priceToEarningsRatio: float = 0.0
    priceToEarningsGrowthRatio: float = 0.0
    debtToEquityRatio: float = 0.0
    freeCashFlowOperatingCashFlowRatio: float = 0.0
    
    # 3. Key Metrics
    currentRatio: float = 0.0
    enterpriseValue: float = 0.0
    returnOnInvestedCapital: float = 0.0
    evToEBITDA: float = 0.0
    incomeQuality: float = 0.0
    grahamNumber: float = 0.0
    
    # 5. Discounted Cash Flow
    dcf: float = 0.0
    
    # 6. Historical
    vwap: float = 0.0
    priceAvg50: float = 0.0
    priceAvg200: float = 0.0
    rsi14: float = 0.0
    
    # 7. Analyst Estimates
    epsLow: float = 0.0
    epsAvg: float = 0.0
    epsHigh: float = 0.0

    # Broker Data
    shortable: bool = False
    fractionable: bool = False

    # Position Data
    qty: float = 0.0
    entry_price: float = 0.0
    pct_profit_and_loss: float = 0.0

    def __repr__(self) -> str:
        """
        Returns a JSON string representation of the DTO.
        
        Returns:
            str: JSON formatted string of attributes.
        """
        return json.dumps(asdict(self), indent=2)

class StockDataTable:
    """
    An abstraction for holding a collection of StockDataDTO objects.
    Ensures that each ticker symbol uniquely maps to its corresponding DTO.
    """
    def __init__(self):
        """Initializes an empty StockDataTable."""
        # [Registry] (1): Initialize the underlying data store for mapping unique symbols.
        self._data: Dict[str, StockDataDTO] = {}

    def add(self, dto: StockDataDTO) -> None:
        """
        Adds or updates a StockDataDTO in the table.
        
        Args:
            dto (StockDataDTO): The data object to add.
        """
        # Validate that the DTO is valid and has a symbol
        if not dto or not getattr(dto, 'symbol', None):
            return
        # [Registry] (2): Register or update the DTO using its symbol as the unique key.
        self._data[dto.symbol] = dto

    def has_ticker(self, symbol: str) -> bool:
        """
        Checks if the table contains a StockDataDTO for the given ticker symbol.
        
        Args:
            symbol (str): The stock ticker symbol.
            
        Returns:
            bool: True if the symbol exists in the table, False otherwise.
        """
        if not symbol or not isinstance(symbol, str):
            return False
        return symbol in self._data

    def get(self, symbol: str) -> Optional[StockDataDTO]:
        """
        Retrieves a StockDataDTO by its ticker symbol.
        
        Args:
            symbol (str): The stock ticker symbol.
            
        Returns:
            Optional[StockDataDTO]: The requested DTO or None if not found.
        """
        # Validate lookup key
        if not symbol or not isinstance(symbol, str):
            return None
        # [Registry] (3): Retrieve the registered DTO by its unique key.
        return self._data.get(symbol)

    def get_all(self) -> List[StockDataDTO]:
        """
        Retrieves all StockDataDTO objects currently in the table.
        
        Returns:
            List[StockDataDTO]: A list of all stored DTOs.
        """
        return list(self._data.values())

    def remove(self, symbol: str) -> None:
        """
        Removes a StockDataDTO from the table by its ticker symbol.
        
        Args:
            symbol (str): The stock ticker symbol to remove.
        """
        # Validate removal key and existence
        if symbol and isinstance(symbol, str) and symbol in self._data:
            del self._data[symbol]

    def __repr__(self) -> str:
        """
        Returns a JSON string representation of the entire table.
        
        Returns:
            str: JSON formatted string mapping symbols to attributes.
        """
        return json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2)

@dataclass
class ActiveOrderDTO:
    """
    A Data Transfer Object representing an active/open order on the broker.
    """
    id: str = ""
    symbol: str = ""
    qty: float = 0.0
    filled_qty: float = 0.0
    side: str = ""
    type: str = ""
    time_in_force: str = ""
    limit_price: float = 0.0
    stop_price: float = 0.0
    status: str = ""

    def __repr__(self) -> str:
        return json.dumps(asdict(self), indent=2)

class ActiveOrderTable:
    """
    An abstraction for holding a collection of ActiveOrderDTO objects.
    Maps order IDs to their corresponding DTOs.
    """
    def __init__(self):
        self._data: Dict[str, ActiveOrderDTO] = {}

    def add(self, dto: ActiveOrderDTO) -> None:
        if not dto or not getattr(dto, 'id', None):
            return
        self._data[dto.id] = dto

    def get(self, order_id: str) -> Optional[ActiveOrderDTO]:
        if not order_id or not isinstance(order_id, str):
            return None
        return self._data.get(order_id)

    def get_all(self) -> List[ActiveOrderDTO]:
        return list(self._data.values())

    def remove(self, order_id: str) -> None:
        if order_id and isinstance(order_id, str) and order_id in self._data:
            del self._data[order_id]

    def __repr__(self) -> str:
        return json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2)

@dataclass
class AccountDTO:
    """
    A Data Transfer Object representing the user's trading account information.
    """
    account_number: str = ""
    status: str = ""
    currency: str = ""
    cash: float = 0.0
    portfolio_value: float = 0.0
    equity: float = 0.0
    buying_power: float = 0.0
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    daytrade_count: int = 0

    def __repr__(self) -> str:
        return json.dumps(asdict(self), indent=2)
