"""
Stock Metrics Module
====================
Defines Data Transfer Objects (DTO) for tracking runtime data.
"""
import json
from dataclasses import dataclass, asdict
from typing import Optional

# [Data Transfer Object (DTO)]: Encapsulates and passes runtime data for a single stock entity.
@dataclass
class StockMetrics:
    """
    A container that clearly keeps track of runtime data for a single stock.
    """
    ticker: str
    price: float
    change_pct_daily: float
    volume: int
    market_cap: int
    sector_industry: Optional[str] = None
    company_name: Optional[str] = None
    
    # Portfolio Metrics
    quantity: float = 0.0
    entry_price: float = 0.0
    change_pct_total: float = 0.0
    
    # Analysis Metrics
    r_squared: Optional[float] = None
    slope: Optional[float] = None
    num_zero_crossings: Optional[int] = None
    mad: Optional[float] = None
    sd: Optional[float] = None

    def __repr__(self):
        """
        Returns a string representation of the StockMetrics.
        
        Returns:
            str: The string representation.
        """
        return json.dumps(asdict(self), indent=2)
