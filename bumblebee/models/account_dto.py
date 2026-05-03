import json
from dataclasses import dataclass, asdict
from .alpaca_datetime import AlpacaDateTimeDTO

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
    last_equity: float = 0.0
    pct_equity_change: float = 0.0
    long_market_value: float = 0.0
    short_market_value: float = 0.0
    position_market_value: float = 0.0
    buying_power: float = 0.0
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    daytrade_count: int = 0
    created_at: str = ""

    @property
    def created_at_parsed(self) -> AlpacaDateTimeDTO:
        return AlpacaDateTimeDTO(self.created_at)

    def __repr__(self) -> str:
        return json.dumps(asdict(self), indent=2)
