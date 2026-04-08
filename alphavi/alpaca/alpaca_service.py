"""
Alpaca API service module.

This module provides the AlpacaService class, responsible for making raw HTTP
requests to the Alpaca API. Optional debug mode (Flask-style) enables writing
response snapshots and report files to disk; otherwise no file I/O is performed.
"""

import os
import json
import requests
from typing import Optional, Any, List
from alphavi_util.core import get_env_var

from alphavi.models import StockDataDTO, StockDataTable, ActiveOrderDTO, ActiveOrderTable, AccountDTO

_DEBUG_LOG_ = "log_alpaca"


class AlpacaService:
    """
    Alpaca API Service.

    This class is implemented as a Singleton to ensure only one instance
    of the HTTP client/configuration exists throughout the application lifecycle.

    Debug mode (``self.debug``) controls all disk writes: raw responses under
    ``debug/``, and ``report()`` output under ``finance_report/``. Pass
    ``debug=True`` or ``debug=False`` on construction; defaults to ``False``.
    The first successful initialization wins.
    """

    _instance = None

    def __new__(
        cls,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        debug: bool = False,
    ):
        # [Singleton] (1): Allocate the single instance if it doesn't exist.
        if cls._instance is None:
            cls._instance = super(AlpacaService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        debug: bool = False,
    ):
        # [Singleton] (2): Initialize configuration once, ignore subsequent __init__ calls.
        if self._initialized:
            return

        self.base_url = base_url or get_env_var("APCA_API_BASE_URL")
        self.api_key = api_key or get_env_var("APCA_API_KEY")
        self.api_secret = api_secret or get_env_var("APCA_API_SECRET_KEY")

        if not self.base_url or not self.api_key or not self.api_secret:
            raise ValueError("Alpaca API credentials are not fully set. Ensure APCA_API_BASE_URL, APCA_API_KEY, and APCA_API_SECRET_KEY are in your environment or .env file.")

        self.debug = bool(debug)

        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }
        self._assets_cache: Optional[List[dict]] = None
        self._initialized = True

    def fetch_endpoint(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """
        Executes a GET request against the Alpaca API and returns the parsed JSON.
        
        Args:
            endpoint (str): The specific API endpoint (e.g., 'account', 'assets').
            params (Optional[dict]): Query parameters to attach to the request.
            
        Returns:
            Any: The JSON response parsed as a Python dict/list, or None on failure/restriction.
        """
        # Ensure we don't have leading slashes in endpoint
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/v2/{clean_endpoint}"
        payload = params.copy() if params else {}
        
        try:
            response = requests.get(url, headers=self.headers, params=payload)

            file_path = None
            if self.debug:
                os.makedirs(_DEBUG_LOG_, exist_ok=True)
                safe_endpoint = clean_endpoint.replace("/", "_")
                if params and "activity_types" in params:
                    safe_endpoint += f"_{params['activity_types']}"
                elif params and "status" in params:
                    safe_endpoint += f"_status_{params['status']}"
                file_path = os.path.join(_DEBUG_LOG_, f"alpaca_{safe_endpoint}.json")

            if response.status_code == 200:
                data = response.json()

                # Client-side filtering: Remove assets where "tradable" is false
                if clean_endpoint.startswith("assets") and isinstance(data, list):
                    data = [item for item in data if item.get("tradable", True)]

                # Client-side filtering fallback: ensure only 'accepted' status if requested
                if clean_endpoint.startswith("orders") and params and params.get("status") == "accepted" and isinstance(data, list):
                    data = [item for item in data if item.get("status") == "accepted"]

                if self.debug and file_path is not None:
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=4)
                return data
            else:
                if self.debug and file_path is not None:
                    try:
                        error_data = response.json()
                        with open(file_path, "w") as f:
                            json.dump({"error_code": response.status_code, "response": error_data}, f, indent=4)
                    except Exception:
                        with open(file_path, "w") as f:
                            f.write(f"Error {response.status_code}: {response.text}")

                print(f"!!! API ERROR (HTTP {response.status_code}): {response.text[:200]}")
                return None
        except Exception as e:
            print(f"!!! CRITICAL ERROR: {e}")
            return None

    def get_tickers(self, includes: List[str], excludes: List[str] = None) -> List[str]:
        """
        Fetches active assets (cached after the first call) and returns a list
        of symbols whose names contain ALL strings in `includes` and NONE of
        the strings in `excludes` (case-insensitive).
        
        Args:
            includes (List[str]): Substrings that MUST be in the asset's name.
            excludes (List[str], optional): Substrings that MUST NOT be in the asset's name.
            
        Returns:
            List[str]: A list of matching asset symbols.
        """
        if self._assets_cache is None:
            print("Fetching active assets from Alpaca API for the first time...")
            data = self.fetch_endpoint("assets", {"status": "active"})
            self._assets_cache = data if data else []
            
        if excludes is None:
            excludes = []
            
        includes_lower = [s.lower() for s in includes]
        excludes_lower = [s.lower() for s in excludes]
        
        matching_tickers = []
        for asset in self._assets_cache:
            name = asset.get("name", "")
            if not name:
                continue
                
            name_lower = name.lower()
            
            # Check if ALL include substrings are present
            if not all(inc in name_lower for inc in includes_lower):
                continue
                
            # Check if ANY exclude substring is present
            if any(exc in name_lower for exc in excludes_lower):
                continue
                
            matching_tickers.append(asset.get("symbol"))
                
        return matching_tickers

    def get_positions(self) -> StockDataTable:
        """
        Fetches all open positions and active assets to form a complete table.
        
        Returns:
            StockDataTable: A populated table of all available assets and current positions.
        """
        table = StockDataTable()
        
        # [Aggregator] (1): Fetch and populate base position data into the cohesive table.
        positions_data = self.fetch_endpoint("positions")
        positions = positions_data if isinstance(positions_data, list) else []
        
        for pos in positions:
            symbol = pos.get("symbol")
            if not symbol:
                continue
            dto = StockDataDTO(symbol=symbol)
            try:
                dto.qty = float(pos.get("qty", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.price = float(pos.get("current_price", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.entry_price = float(pos.get("avg_entry_price", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.latestChangePercent = float(pos.get("change_today", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.pct_profit_and_loss = float(pos.get("unrealized_plpc", 0.0))
            except (ValueError, TypeError):
                pass
            table.add(dto)
            
        # [Aggregator] (2): Fetch and merge subsequent asset data stream into the structure efficiently.
        assets_data = self.fetch_endpoint("assets", {"status": "active"})
        assets = assets_data if isinstance(assets_data, list) else []
        
        for asset in assets:
            symbol = asset.get("symbol")
            if not symbol:
                continue
                
            if table.has_ticker(symbol):
                dto = table.get(symbol)
                dto.shortable = asset.get("shortable", False)
                dto.fractionable = asset.get("fractionable", False)
                dto.name = asset.get("name", "")
            else:
                dto = StockDataDTO(symbol=symbol)
                dto.shortable = asset.get("shortable", False)
                dto.fractionable = asset.get("fractionable", False)
                dto.name = asset.get("name", "")
                table.add(dto)
                
        return table
                
    def get_orders(self) -> ActiveOrderTable:
        """
        Fetches the current open/accepted orders without caching.
        
        Returns:
            ActiveOrderTable: A table containing all ActiveOrderDTO objects.
        """
        table = ActiveOrderTable()
        data = self.fetch_endpoint("orders", {"status": "accepted"})
        if not data or not isinstance(data, list):
            return table
            
        for item in data:
            dto = ActiveOrderDTO()
            dto.id = item.get("id", "")
            dto.symbol = item.get("symbol", "")
            try:
                dto.qty = float(item.get("qty") or 0.0)
            except (ValueError, TypeError):
                pass
            try:
                dto.filled_qty = float(item.get("filled_qty") or 0.0)
            except (ValueError, TypeError):
                pass
            dto.side = item.get("side", "")
            dto.type = item.get("type", "")
            dto.time_in_force = item.get("time_in_force", "")
            try:
                dto.limit_price = float(item.get("limit_price") or 0.0)
            except (ValueError, TypeError):
                pass
            try:
                dto.stop_price = float(item.get("stop_price") or 0.0)
            except (ValueError, TypeError):
                pass
            dto.status = item.get("status", "")
            table.add(dto)
            
        return table

    def get_account_info(self) -> AccountDTO:
        """
        Fetches the current account information without caching.
        
        Returns:
            AccountDTO: A data transfer object populated with account metrics.
        """
        dto = AccountDTO()
        data = self.fetch_endpoint("account")
        if not data or not isinstance(data, dict):
            return dto
            
        dto.account_number = data.get("account_number", "")
        dto.status = data.get("status", "")
        dto.currency = data.get("currency", "")
        try:
            dto.cash = float(data.get("cash", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.portfolio_value = float(data.get("portfolio_value", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.equity = float(data.get("equity", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.buying_power = float(data.get("buying_power", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.initial_margin = float(data.get("initial_margin", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.maintenance_margin = float(data.get("maintenance_margin", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.daytrade_count = int(data.get("daytrade_count", 0))
        except (ValueError, TypeError):
            pass
            
        return dto

    def get_stock_data(self, ticker: str) -> StockDataDTO:
        """
        Fetches the position information for a specific ticker and returns
        it as a StockDataDTO.
        
        Args:
            ticker (str): The stock symbol to query (e.g., 'AAPL').
            
        Returns:
            StockDataDTO: A data transfer object populated with position metrics.
        """
        dto = StockDataDTO(symbol=ticker)
        
        # Fetch all positions in real-time
        data = self.fetch_endpoint("positions")
        positions = data if isinstance(data, list) else []
            
        # Find the position in the fetched data
        for position in positions:
            if position.get("symbol") == ticker:
                try:
                    dto.qty = float(position.get("qty", 0.0))
                except (ValueError, TypeError):
                    pass
                try:
                    dto.price = float(position.get("current_price", 0.0))
                except (ValueError, TypeError):
                    pass
                try:
                    dto.entry_price = float(position.get("avg_entry_price", 0.0))
                except (ValueError, TypeError):
                    pass
                try:
                    dto.latestChangePercent = float(position.get("change_today", 0.0))
                except (ValueError, TypeError):
                    pass
                try:
                    dto.pct_profit_and_loss = float(position.get("unrealized_plpc", 0.0))
                except (ValueError, TypeError):
                    pass
                break
                
        return dto

    def report(self) -> None:
        """
        Fetches various account activities and positions, and saves them
        as JSON files into the 'finance_report' folder.

        No-op when debug mode is off (no API calls and no file I/O).
        """
        if self.debug:
            pass
        

        if (not self.debug): os.makedirs("finance_report", exist_ok=True)
        

        endpoints = {
            "transactions.json": ("account/activities", {"activity_types": "FILL", "limit": 100}),
            "positions.json": ("positions", None),
            "journal_entries.json": ("account/activities", {"activity_types": "JNLC", "limit": 100}),
            "interests.json": ("account/activities", {"activity_types": "INT", "limit": 100}),
            "fees.json": ("account/activities", {"activity_types": "FEE", "limit": 100}),
            "dividends.json": ("account/activities", {"activity_types": "DIV", "limit": 100})
        }
        for filename, (endpoint, params) in endpoints.items():
            data = self.fetch_endpoint(endpoint, params)
            if not self.debug and data is not None:
                file_path = os.path.join("finance_report", filename)
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"Saved {filename} to finance_report directory.")
