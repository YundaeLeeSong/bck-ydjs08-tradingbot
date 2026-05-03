"""
Alpaca API service module.

This module provides the AlpacaService class, responsible for making raw HTTP
requests to the Alpaca API. Optional debug mode (Flask-style) enables writing
response snapshots and report files to disk; otherwise no file I/O is performed.
"""

import os
import json
import math
import requests
from typing import Optional, Any, List
from ydjs_util.core import get_env_var

from bumblebee.models import StockDataDTO, StockDataTable, ActiveOrderDTO, ActiveOrderTable, AccountDTO, AlpacaDateTimeDTO
from bumblebee.est_timer import ESTTimer

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
            account = self.get_account_info()
            # print(f'[DEBUG] hi, your purchasing power is now, ${self.get_unit_value(account):.2f} for rebalance, long: {self.is_long(account)}, short: {self.is_short(account)}')
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
        
        account = self.get_account_info()
        print(f'[DEBUG] hi, your purchasing power is now, ${self.get_unit_value(account):.2f} for rebalance, long: {self.is_long(account)}, short: {self.is_short(account)}')

    def fetch_endpoint(self, endpoint: str, params: Optional[dict] = None, method: str = "GET", data: Optional[dict] = None) -> Any:
        """
        Executes a request against the Alpaca API and returns the parsed JSON.
        
        Args:
            endpoint (str): The specific API endpoint (e.g., 'account', 'assets').
            params (Optional[dict]): Query parameters to attach to the request.
            method (str): The HTTP method ('GET', 'POST', 'DELETE'). Defaults to 'GET'.
            data (Optional[dict]): The JSON payload for POST requests.
            
        Returns:
            Any: The JSON response parsed as a Python dict/list, or None on failure/restriction.
        """
        # Ensure we don't have leading slashes in endpoint
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/v2/{clean_endpoint}"
        payload = params.copy() if params else {}
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=payload)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, params=payload, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers, params=payload)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            file_path = None
            if self.debug:
                os.makedirs(_DEBUG_LOG_, exist_ok=True)
                safe_endpoint = clean_endpoint.replace("/", "_")
                if method.upper() != "GET":
                    safe_endpoint = f"{method.lower()}_{safe_endpoint}"
                if params and "activity_types" in params:
                    safe_endpoint += f"_{params['activity_types']}"
                elif params and "status" in params:
                    safe_endpoint += f"_status_{params['status']}"
                file_path = os.path.join(_DEBUG_LOG_, f"alpaca_{safe_endpoint}.json")

            if response.status_code in (200, 201, 204):
                if response.status_code == 204 or not response.text:
                    resp_data = {}
                else:
                    resp_data = response.json()

                # Client-side filtering: Remove assets where "tradable" is false
                if clean_endpoint.startswith("assets") and isinstance(resp_data, list):
                    resp_data = [item for item in resp_data if item.get("tradable", True)]

                # Client-side filtering fallback: ensure only 'accepted' status if requested
                if method.upper() == "GET" and clean_endpoint.startswith("orders") and params and params.get("status") == "accepted" and isinstance(resp_data, list):
                    resp_data = [item for item in resp_data if item.get("status") == "accepted"]

                if self.debug and file_path is not None:
                    with open(file_path, "w") as f:
                        json.dump(resp_data, f, indent=4)
                return resp_data
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
            dto.isActive = True
            try:
                dto.qty = float(pos.get("qty", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.rt_price = float(pos.get("current_price", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.entry_price = float(pos.get("avg_entry_price", 0.0))
            except (ValueError, TypeError):
                pass
            try:
                dto.pct_day_pnl = float(pos.get("change_today", 0.0)) * 100
            except (ValueError, TypeError):
                pass
            try:
                dto.pct_net_pnl = float(pos.get("unrealized_plpc", 0.0)) * 100
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
        data = self.fetch_endpoint("orders", {"status": "open", "limit": 500})
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
            dto.long_market_value = float(data.get("long_market_value", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.short_market_value = float(data.get("short_market_value", 0.0))
        except (ValueError, TypeError):
            pass
        try:
            dto.position_market_value = float(data.get("position_market_value", 0.0))
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

        dto.created_at = data.get("created_at", "")
        try:
            dto.last_equity = float(data.get("last_equity", 0.0))
        except (ValueError, TypeError):
            pass

        if dto.last_equity > 0:
            dto.pct_equity_change = ((dto.equity - dto.last_equity) / dto.last_equity) * 100.0
            if abs(dto.pct_equity_change - 0) < 0.001: dto.pct_equity_change = 0
            
        return dto

    def get_unit_value(self, account: Optional[AccountDTO] = None) -> float:
        """
        Calculates the unit value dynamically.
        Formula: (equity - maintenance_margin) / 120.0
        """
        account = account or self.get_account_info()
        return (account.equity - account.maintenance_margin) / 120.0

    def get_cash_rate(self, account: Optional[AccountDTO] = None) -> float:
        """
        Returns the ratio of cash to equity in the account.
        """
        account = account or self.get_account_info()
        if account.equity <= 0:
            return 0.0
        return account.cash / account.equity

    def is_entry(self, account: Optional[AccountDTO] = None) -> bool:
        """
        Returns true if the cash-to-equity ratio is greater than 0.7 (70%).
        """
        return self.get_cash_rate(account) > 0.7

    def is_long(self, account: Optional[AccountDTO] = None) -> bool:
        """
        Determines if the account is in a healthy state to open new long positions.
        """
        account = account or self.get_account_info()
        
        # Prevent division by zero
        if account.maintenance_margin <= 0 or account.equity <= 0:
            return False

        # 1. Check margin health (>1.5 ratio)
        if (account.equity / account.maintenance_margin) <= 1.5:
            return False
        
        # 2. Check liquid cash reserve (>15% of equity)
        if (account.cash / account.equity) <= 0.15:
            return False

        return True

    def is_short(self, account: Optional[AccountDTO] = None) -> bool:
        """
        Determines if the account is in a healthy state to open new short positions.
        """
        account = account or self.get_account_info()

        # Prevent division by zero
        if account.maintenance_margin <= 0 or account.equity <= 0 or account.long_market_value <= 0:
            return False

        # 1. Check margin health (>1.5 ratio)
        if (account.equity / account.maintenance_margin) <= 1.5:
            return False

        # 2. Check long collateral (>50% of equity)
        if (account.long_market_value / account.equity) <= 0.5:
            return False

        # 3. Check short exposure limit (<50% of long portfolio)
        if (abs(account.short_market_value) / account.long_market_value) >= 0.5:
            return False
        
        # 4. Ensure positive buying power
        if account.buying_power <= 0:
            return False

        return True

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
        dto.isActive = True
        
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
                    dto.rt_price = float(position.get("current_price", 0.0))
                except (ValueError, TypeError):
                    pass
                try:
                    dto.entry_price = float(position.get("avg_entry_price", 0.0))
                except (ValueError, TypeError):
                    pass
                try:
                    dto.pct_latest_change = float(position.get("change_today", 0.0)) * 100
                except (ValueError, TypeError):
                    pass
                try:
                    dto.pct_profit_and_loss = float(position.get("unrealized_plpc", 0.0)) * 100
                except (ValueError, TypeError):
                    pass
                break
                
        # Fetch asset info to get shortable and fractionable status
        asset_data = self.fetch_endpoint(f"assets/{ticker}")
        # print(asset_data)
        if asset_data and isinstance(asset_data, dict):
            dto.shortable = asset_data.get("shortable", False)
            dto.fractionable = asset_data.get("fractionable", False)
            if not dto.name:
                dto.name = asset_data.get("name", "")
                
        return dto

    def _delete_order(self, dto: StockDataDTO, current_orders: Optional[ActiveOrderTable] = None) -> None:
        """
        Internal: Cancels all open orders for a specific ticker.
        If `current_orders` is provided, skips fetching the orders again.
        """
        open_orders = current_orders or self.get_orders()
        for order in open_orders.get_all():
            if order.symbol == dto.symbol:
                response = self.fetch_endpoint(f"orders/{order.id}", method="DELETE")
                if response is not None:
                    print(f"  [OK] Canceled order {order.id} for {dto.symbol}")

    def delete_all_orders(self) -> None:
        """
        Cancels all open orders currently active in the account.
        """
        open_orders = self.get_orders()
        orders_list = open_orders.get_all()
        if not orders_list:
            print("  [INFO] No opened orders to delete.")
            return

        for order in orders_list:
            response = self.fetch_endpoint(f"orders/{order.id}", method="DELETE")
            if response is not None:
                print(f"  [OK] Canceled order {order.id} for {order.symbol}")

    def post_order(self, dto: StockDataDTO, side: str, qty: float, limit_price: float, current_orders: Optional[ActiveOrderTable] = None) -> Optional[dict]:
        """
        Places a limit order for the given asset symbol.
        Enforces day-only Time-in-Force and dynamically calculates extended hours.
        Quantities and prices are polished and validated before posting.
        Also guarantees any existing open orders for this ticker are deleted first.
        Pass `current_orders` if performing batch operations to prevent redundant API fetches.
        """
        if side not in ("buy", "sell"): 
            raise ValueError(f"side must be 'buy' or 'sell', got: {side}")
            
        # 1. Polish
        polished_price = round(limit_price, 2)
        polished_qty = round(qty, 2)
        if not dto.fractionable: polished_qty = float(math.floor(qty))   # non-fract
        if dto.qty == 0: polished_qty = float(math.floor(qty))           # short
        
        # 2. Validate
        if polished_qty <= 0 or polished_price <= 0:
            print(f"[DEBUG] Invalid order for {dto.symbol}: "
                  f"qty={polished_qty}, price={polished_price}. Must be > 0.")
            return None

        # 3. Short selling validation
        if (not dto.shortable and side == "sell" and dto.qty == 0):
            print(f"[DEBUG] Cannot short sell {dto.symbol}: "
                  f"Asset is not shortable (requested: {polished_qty}, owned: {dto.qty}).")
            return None
        
        if (side == "sell" and dto.qty > 0 and polished_qty > dto.qty):
            print(f"[DEBUG] Cannot sell {dto.symbol}: "
                  f"You should sell off ALL the long position "
                  f"**{dto.qty} > 0** shares you own (requested: {polished_qty}, owned: {dto.qty}).")
            return None

        # 4. Clean slate: Delete existing orders for this specific ticker
        self._delete_order(dto, current_orders=current_orders)

        # 5. Post the new order
        payload = {
            "symbol": dto.symbol,
            "side": side,
            "type": "limit",
            "time_in_force": "day",
            "qty": polished_qty,
            "limit_price": polished_price,
            "extended_hours": ESTTimer().is_extended_hours()
        }
        
        response = self.fetch_endpoint("orders", method="POST", data=payload)
        if response is not None and self.debug:
            print(f"  [OK] Limit {side} order placed: [{dto.symbol}] {polished_qty} @ ${polished_price} = ${polished_qty * polished_price:.2f},, original price: ${dto.rt_price:.2f} with amplitude: {max(dto.pct_mad, dto.pct_sd):.2f}%")
        return response

    def _fetch_activities(self, after: Optional[AlpacaDateTimeDTO] = None, until: Optional[AlpacaDateTimeDTO] = None) -> List[Any]:
        params = {"direction": "asc"}
        if after and after.raw: params["after"] = after.raw
        if until and until.raw: params["until"] = until.raw
        
        all_activities = []
        
        while True:
            response = self.fetch_endpoint("account/activities", params)
            if not response or not isinstance(response, list):
                break
            
            all_activities.extend(response)
            
            if len(response) < 100:  # Assuming default page_size is 100
                break
                
            # [Pagination] Use the ID of the last item in the current batch as the anchor 
            # for the next request. With direction="asc", the API will return activities 
            # created strictly after this ID.
            params["page_token"] = response[-1]["id"]  # Set anchor ID to fetch next 100 items starting AFTER this one
            
        if self.debug:
            os.makedirs(_DEBUG_LOG_, exist_ok=True)
            file_path = os.path.join(_DEBUG_LOG_, "alpaca_account_activities.json")
            with open(file_path, "w") as f:
                json.dump(all_activities, f, indent=4)

        return all_activities

    def report(self, after: Optional[AlpacaDateTimeDTO] = None, until: Optional[AlpacaDateTimeDTO] = None) -> None:
        """
        Fetches various account activities and positions, and saves them
        as JSON files into the 'finance_report' folder (or 'finance_report/all' if range provided).

        No-op when debug mode is off (no API calls and no file I/O).
        """
        if not self.debug:
            return
        
        report_dir = "finance_report"
        if after or until:
            after_str = after.date_str if after else ""
            until_str = until.date_str if until else ""
            report_dir = os.path.join(report_dir, f"{after_str}_to_{until_str}" if after_str and until_str else "range")
        os.makedirs(report_dir, exist_ok=True)

        data_map = {
            "activities.json": self._fetch_activities(after, until),
            "positions.json": self.fetch_endpoint("positions")
        }

        for filename, data in data_map.items():
            if data is not None:
                file_path = os.path.join(report_dir, filename)
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"Saved {filename} to {report_dir} directory.")
