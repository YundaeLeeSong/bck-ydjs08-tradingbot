"""
Models Module
=============
Defines Data Transfer Objects (DTO) for tracking runtime data.
"""
from dataclasses import dataclass
from typing import List, Optional

# Pattern: Data Transfer Object (DTO)
@dataclass
class TickerRuntimeData:
    """
    A container that clearly keeps track of runtime data for a single stock.
    """
    ticker: str
    price: float
    change_pct: float
    volume: int
    market_cap: int
    sector: Optional[str] = None
    
    # Analysis Metrics
    r_squared: Optional[float] = None
    slope: Optional[float] = None
    num_zero_crossings: Optional[int] = None
    mad: Optional[float] = None
    sd: Optional[float] = None

class AnalysisSession:
    """
    Pattern: Registry / State
    Keeps track of multiple TickerRuntimeData models over the course of a pipeline run.
    """
    def __init__(self, name: str):
        self.name = name
        self.results: List[TickerRuntimeData] = []
        
    def add_result(self, result: TickerRuntimeData):
        self.results.append(result)
