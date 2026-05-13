import json
from dataclasses import dataclass, asdict

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
