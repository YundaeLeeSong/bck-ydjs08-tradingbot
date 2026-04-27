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
    # 0. internal logic flags
    isActive: bool = False
    isAnalyzed: bool = False
    # 1. Profile
    symbol: str = ""
    name: str = ""
    industry: str = ""
    sector: str = ""
    marketCap: float = 0.0
    beta: float = 0.0
    volume: int = 0
    averageVolume: int = 0
    # 1. Position Data
    qty: float = 0.0 # running data (Alpaca)
    entry_price: float = 0.0 # running data (Alpaca)
    rt_price: float = 0.0
    price: float = 0.0
    dcf: float = 0.0 # Discounted Cash Flow (fmp)
    vwap: float = 0.0 # Volume Weighted Average Price (fmp)
    # 2. Percent Change Indicators
    pct_mad: float = 0.0 # pnl daily percent change, mean abolute deviation (fmp)
    pct_sd: float = 0.0 # pnl daily percent change, standard deviation (fmp)
    pct_day_pnl: float = 0.0 # daily pnl (Alpaca) 
    pct_net_pnl: float = 0.0 # accumulated pnl (Alpaca)
    
    # 3. Historical
    priceAvg50: float = 0.0     # Simple Moving Average (SMA) - 50 days (yfinance)
    priceAvg200: float = 0.0    # Simple Moving Average (SMA) - 200 days (yfinance)
    rsi14: float = 0.0          # Relative Strength Index 14 - momentum oscillator (yfinance)
    r_squared: float = 0.0
    slope: float = 0.0
    zero_freq: int = 0
    
    # 4. Ratios
    priceToEarningsRatio: float = 0.0
    priceToEarningsGrowthRatio: float = 0.0
    debtToEquityRatio: float = 0.0
    freeCashFlowOperatingCashFlowRatio: float = 0.0
    
    # 5. Key Metrics
    currentRatio: float = 0.0
    enterpriseValue: float = 0.0
    returnOnInvestedCapital: float = 0.0
    evToEBITDA: float = 0.0
    incomeQuality: float = 0.0
    grahamNumber: float = 0.0
    
    # 6. Broker Data (Alpaca)
    shortable: bool = False
    fractionable: bool = False
    
    # 7. Analyst Estimates
    epsLow: float = 0.0     # Earnings Per Share (fmp)
    epsAvg: float = 0.0     # Earnings Per Share (fmp)
    epsHigh: float = 0.0    # Earnings Per Share (fmp)



    def __repr__(self) -> str:
        """
        Returns a JSON string representation of the DTO.
        
        Returns:
            str: JSON formatted string of attributes.
        """
        return json.dumps(asdict(self), indent=2)

    def override(self, other: 'StockDataDTO') -> 'StockDataDTO':
        """
        Returns a new StockDataDTO by overriding self's attributes with other's attributes.
        An attribute in 'other' is considered defined if it is not its initial/default value.
        """
        from dataclasses import fields
        result = StockDataDTO()
        for f in fields(self):
            name = f.name
            self_val = getattr(self, name)
            other_val = getattr(other, name)
            
            # If the attribute in 'other' is defined (not its default value), it wins
            if other_val != f.default:
                setattr(result, name, other_val)
            else:
                setattr(result, name, self_val)
        return result

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
        if not symbol or not isinstance(symbol, str): return None
        # [Registry] (3): Retrieve the registered DTO by its unique key.
        return self._data.get(symbol)

    def get_all(self, active_only: bool = False) -> List[StockDataDTO]:
        """
        Retrieves all StockDataDTO objects currently in the table.
        
        Args:
            active_only (bool): If True, returns only rows where isActive is True.
            
        Returns:
            List[StockDataDTO]: A list of stored DTOs.
        """
        if active_only: return [dto for dto in self._data.values() if getattr(dto, 'isActive', False)]
        return list(self._data.values())

    def get_tickers(self, active_only: bool = False) -> List[str]:
        """
        Retrieves all ticker symbols currently in the table.
        
        Args:
            active_only (bool): If True, returns only symbols where isActive is True.
            
        Returns:
            List[str]: A list of stored ticker symbols.
        """
        if active_only: return [symbol for symbol, dto in self._data.items() if getattr(dto, 'isActive', False)]
        return list(self._data.keys())

    def remove(self, symbol: str) -> None:
        """
        Removes a StockDataDTO from the table by its ticker symbol.
        
        Args:
            symbol (str): The stock ticker symbol to remove.
        """
        # Validate removal key and existence
        if symbol and isinstance(symbol, str) and symbol in self._data:
            del self._data[symbol]

    def override(self, other: 'StockDataTable') -> 'StockDataTable':
        """
        Returns a new StockDataTable by overriding this table's rows with other's rows.
        Raises KeyError if this table has a key that is missing in the other table.
        """
        result = StockDataTable()
        for symbol, dto in self._data.items():
            if symbol not in other._data:
                raise KeyError(f"Key '{symbol}' found in self but not in other table.")
            result.add(dto.override(other._data[symbol]))
        return result

    def __repr__(self) -> str:
        """
        Returns a JSON string representation of the entire table.
        
        Returns:
            str: JSON formatted string mapping symbols to attributes.
        """
        return json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2)

    def __iter__(self):
        """
        Returns an iterator over the StockDataDTO objects in the table.
        """
        return iter(self._data.values())

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
    long_market_value: float = 0.0
    short_market_value: float = 0.0
    position_market_value: float = 0.0
    buying_power: float = 0.0
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    daytrade_count: int = 0

    def __repr__(self) -> str:
        return json.dumps(asdict(self), indent=2)
