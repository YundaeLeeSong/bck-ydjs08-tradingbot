import json
from dataclasses import dataclass, asdict, fields

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

    # 8. Reporting Data
    total_cash_spent: float = 0.0
    total_cash_received: float = 0.0
    total_dividend: float = 0.0
    total_position_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_operational_pnl: float = 0.0
    net_pnl: float = 0.0

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
