import json
from dataclasses import asdict
from typing import Dict, List, Optional
from .stock_data_dto import StockDataDTO

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
            
        for symbol, dto in other._data.items():
            if symbol in self._data.keys(): result.add(dto.override(self._data[symbol]))
            else: result.add(dto)
        return result

    def __repr__(self) -> str:
        """
        Returns a JSON string representation of the entire table.
        
        Returns:
            str: JSON formatted string mapping symbols to attributes.
        """
        return json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2)
