from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

@dataclass
class AlpacaDateTimeDTO:
    """
    A helper Data Transfer Object for parsing Alpaca datetime strings (RFC 3339).
    Provides properties to easily extract standard Python datetime objects, dates, and times.
    """
    raw: str = ""

    @classmethod
    def now(cls) -> 'AlpacaDateTimeDTO':
        """
        [Factory] (1): Creates a new AlpacaDateTimeDTO representing the current UTC time in RFC 3339 format.
        """
        # Format: 2025-06-15T17:01:51.652171Z
        now_utc = datetime.now(timezone.utc)
        return cls(raw=now_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))

    @property
    def dt(self) -> Optional[datetime]:
        """Returns the standard Python tz-aware datetime object."""
        if not self.raw:
            return None
        try:
            return datetime.fromisoformat(self.raw.replace('Z', '+00:00'))
        except ValueError:
            return None

    @property
    def date_str(self) -> str:
        """Returns the date component as 'YYYY-MM-DD'."""
        dt_obj = self.dt
        return dt_obj.strftime("%Y-%m-%d") if dt_obj else ""

    @property
    def time_str(self) -> str:
        """Returns the time component as 'HH:MM:SS'."""
        dt_obj = self.dt
        return dt_obj.strftime("%H:%M:%S") if dt_obj else ""
