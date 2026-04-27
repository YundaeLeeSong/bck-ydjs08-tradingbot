"""
Framework module for the alphavi project.

Provides the base trading framework that defines the skeleton of the trading
strategy, deferring specific implementation steps to subclasses.
"""

from typing import List, Optional
from bumblebee.external import AlpacaService
from bumblebee.external import YFinanceService
from bumblebee.models import AccountDTO, ActiveOrderTable, StockDataTable

import os
def _logfile(name: str, table, active_only: bool = True):
    os.makedirs("log", exist_ok=True)
    log_file = os.path.join("log", f"{name.lower().replace(' ', '_')}.json")
    
    if hasattr(table, 'get_all'):
        import json
        from dataclasses import asdict
        try:
            dtos = table.get_all(active_only=active_only)
        except TypeError:
            dtos = table.get_all()
            
        filtered_data = {}
        for dto in dtos:
            key = getattr(dto, 'symbol', getattr(dto, 'id', None))
            if key is not None:
                filtered_data[key] = asdict(dto)
        content = json.dumps(filtered_data, indent=2)
    else:
        content = repr(table)
        
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(content)





class Bumblebee:
    """
    Base class for trading strategy execution.
    """
    
    def __init__(self, name: str = "Bumblebee", **kwargs):
        """
        Initializes the framework with required API services and fetches initial state.
        Allows overriding methods by passing them as kwargs (e.g., stock_up_long=my_custom_func).
        
        Args:
            name (str): The name of the bot instance.
            **kwargs: Functions to override the default template methods.
        """
        self.name = name
        print(f"\n--- Starting Trading Bot @ {name} ---")
        
        # [Strategy] Allow dynamic method overriding via kwargs
        for key, value in kwargs.items():
            if callable(value) and hasattr(self, key):
                # Bind the function to this instance
                setattr(self, key, value.__get__(self, self.__class__))
                
        self.account_dto: AccountDTO = AlpacaService().get_account_info()
        self.orders_table: ActiveOrderTable = AlpacaService().get_orders()
        self._positions: StockDataTable = AlpacaService().get_positions()

        self.unit_value: float = AlpacaService().get_unit_value(self.account_dto)
        self.is_entry: bool = AlpacaService().is_entry(self.account_dto)
        self.is_long: bool = AlpacaService().is_long(self.account_dto)
        self.is_short: bool = AlpacaService().is_short(self.account_dto)

        self.position_tickers: List[str] = self._positions.get_tickers(active_only=True)

        self.option_tickers: List[str] = (
            AlpacaService().get_tickers(["YieldMax"], ["Short"]) + 
            AlpacaService().get_tickers(["Roundhill", "WeeklyPay"])
        )
        self.option_tickers_inv: List[str] = AlpacaService().get_tickers(["YieldMax", "Short"])

        self.index_tickers: List[str] = AlpacaService().get_tickers(["MicroSectors"], ["Inverse", "due"])

        self.index_tickers_x2: List[str] = (
            AlpacaService().get_tickers(["Bull", "2X"]) + 
            AlpacaService().get_tickers(["Leveraged", "2X"], ["Inverse"])
        )

        self.index_tickers_x3: List[str] = (
            AlpacaService().get_tickers(["Bull", "3X"]) + 
            AlpacaService().get_tickers(["Leveraged", "3X"], ["Inverse"])
        )

        self.winning_tickers_to_short: List[str] = YFinanceService().get_winner_tickers(
            max_mcap=100_000_000_000,
            min_change=15.0
        )
        YFinanceService().get_stocks_table(
            tickers=self.winning_tickers_to_short, 
            graph_path="market_report/shorting"
        )

        self.loser_tickers_to_long: List[str] = YFinanceService().get_loser_tickers(
            min_mcap=100_000_000_000,
            max_change=-4.5
        )
        YFinanceService().get_stocks_table(
            tickers=self.loser_tickers_to_long, 
            graph_path="market_report/longing"
        )


        yfinance_table = YFinanceService().get_stocks_table(self.loser_tickers_to_long + self.position_tickers)
        self.active_long_positions: StockDataTable = yfinance_table.override(self._positions)
        _logfile("positions", self._positions, active_only=False)
        _logfile("positions (actives)", self._positions)
        _logfile("long positions", self.active_long_positions, active_only=False)
        _logfile("long positions (actives)", self.active_long_positions)

        


        self._report_state()

    def _report_state(self) -> None:
        """
        Reports the instance variables value on console.
        """
        print("\n" + "="*60)
        print(" TRADING FRAMEWORK INITIALIZATION REPORT")
        print("="*60)
        print(f"[Account] Unit Value:           ${self.unit_value:.2f}")
        print(f"[Account] Is Entry:             {self.is_entry}")
        print(f"[Account] Is Long:              {self.is_long}")
        print(f"[Account] Is Short:             {self.is_short}")
        print(f"[Account] Open Orders:          {len(self.orders_table.get_all())}")
        print(f"[Data] Position Tickers Amount: {len(self.active_long_positions.get_tickers())}")
        print(f"[Data] Option Tickers:          {self.option_tickers}")
        print(f"[Data] Option Tickers Inv:      {self.option_tickers_inv}")
        print(f"[Data] Index Tickers:           {self.index_tickers}")
        print(f"[Data] Index Tickers x2:        {self.index_tickers_x2}")
        print(f"[Data] Index Tickers x3:        {self.index_tickers_x3}")
        print(f"[Data] Winning Tickers (Short): {self.winning_tickers_to_short}")
        print(f"[Data] Loser Tickers (Long):    {self.loser_tickers_to_long}")
        print("="*60 + "\n")

    def _post_order(self, dto, side: str, qty: float, limit_price: float = 0.0) -> None:
        """
        Internal method to handle posting orders using the session's open orders.
        """
        AlpacaService().post_order(
            dto,
            side=side,
            qty=qty,
            limit_price=limit_price,
            current_orders=self.orders_table
        )

    def execute(self) -> None:
        """
        Executes the overall trading algorithmic sequence.
        """
        # [TemplateMethod] (1): Define the skeleton of the algorithm, invoking deferred logic.
        self.initialize()
        
        if self.is_long:
            self.rebalance("long", "soft")
            self.rebalance("long", "hard")
            self.liquidate("long")
            self.close("long")
            
        if self.is_short:
            self.rebalance("short", "soft")
            self.rebalance("short", "hard")
            self.liquidate("short")
            self.close("short")

    # --- Public API for external orchestration ---
    
    def initialize(self) -> None:
        """Executes initialization steps for the trading strategy."""
        pass

    def rebalance(self, side: str, mode: str) -> None:
        if side not in ("long", "short"):
            raise ValueError("side must be 'long' or 'short'")
        if mode not in ("soft", "hard"):
            raise ValueError("mode must be 'soft' or 'hard'")

        if side == "long" and mode == "soft":
            self._soft_rebalance_long()
        elif side == "long" and mode == "hard":
            self._hard_rebalance_long()
        elif side == "short" and mode == "soft":
            self._soft_rebalance_short()
        elif side == "short" and mode == "hard":
            self._hard_rebalance_short()

    def liquidate(self, side: str) -> None:
        if side == "long":
            self._liquidate_long()
        elif side == "short":
            self._liquidate_short()
        else:
            raise ValueError("side must be 'long' or 'short'")

    def close(self, side: str) -> None:
        if side == "long":
            self._close_long()
        elif side == "short":
            self._close_short()
        else:
            raise ValueError("side must be 'long' or 'short'")

    # [TemplateMethod] (2): Primitive operations to be implemented by concrete subclasses.
    
    def _soft_rebalance_long(self) -> None:
        """Executes logic for stocking up long positions (soft rebalance)."""
        # 1. all positions dto should be done this, dto = yf_dto.override(alpaca_dto)
        for alpaca_dto in self.active_long_positions.get_all():
            # print(alpaca_dto)
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            # qty validate
            if alpaca_dto.qty < 0: continue # short position
            dto = YFinanceService().get_stock_data(alpaca_dto.symbol).override(alpaca_dto)
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price) if p > 0]
            if not available_prices: continue # no price data
            floor_price = min(available_prices)
            ceil_price = max(available_prices)
            if 4 * self.unit_value < floor_price: continue # overpriced relative to account
            ##################################################################
            ###### LOGIC
            ##################################################################
            if (dto.pct_net_pnl < -10 * pct_amp or 4 * pct_amp < dto.pct_net_pnl): # big lost/gained tickers
                notional_value = self.unit_value / 4
                buy_price = floor_price * (1 - (1.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            elif (dto.qty == 0.01 or dto.qty == 0): # tickers to new entry
                notional_value = self.unit_value / 7
                buy_price = floor_price * (1 - (0.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            else: continue 
            # calculation, constant notional value, consistent buying
            # order
            self._post_order(dto, 
                side="buy", 
                qty=raw_qty, 
                limit_price=buy_price
            )

    def _hard_rebalance_long(self) -> None:
        """Executes logic for hard rebalancing long positions."""
        pass

    def _liquidate_long(self) -> None:
        """Executes logic for liquidating long positions."""
        pass

    def _soft_rebalance_short(self) -> None:
        """Executes logic for stocking up short positions (soft rebalance)."""
        pass

    def _hard_rebalance_short(self) -> None:
        """Executes logic for hard rebalancing short positions."""
        pass

    def _liquidate_short(self) -> None:
        """Executes logic for liquidating short positions."""
        pass

    def _close_long(self) -> None:
        """Executes logic for closing long positions."""
        # 1. all positions dto should be done this, dto = yf_dto.override(alpaca_dto)
        for alpaca_dto in self._positions.get_all(active_only=True):
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            if (dto.pct_net_pnl < 2 * pct_amp): continue
            # qty validate
            if alpaca_dto.qty <= 0.01: continue
            dto = YFinanceService().get_stock_data(alpaca_dto.symbol).override(alpaca_dto)
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price, dto.entry_price) if p > 0]
            if not available_prices: continue # no price data
            floor_price = min(available_prices)
            ceil_price = max(available_prices)
            ##################################################################
            ###### LOGIC
            ##################################################################
            buy_price = ceil_price * (1 + (0.4 * pct_amp / 100.0))
            raw_qty = abs(dto.qty) - 0.01
            # order
            self._post_order(dto, 
                side="sell", 
                qty=raw_qty, 
                limit_price=buy_price
            )

    def _close_short(self) -> None:
        """Executes logic for closing short positions."""
        # 1. all positions dto should be done this, dto = yf_dto.override(alpaca_dto)
        for alpaca_dto in self._positions.get_all(active_only=True):
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            # qty validate
            if alpaca_dto.qty > 0: continue
            dto = YFinanceService().get_stock_data(alpaca_dto.symbol).override(alpaca_dto)
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price, dto.entry_price) if p > 0]
            if not available_prices: continue # no price data
            floor_price = min(available_prices)
            ceil_price = max(available_prices)
            ##################################################################
            ###### LOGIC
            ##################################################################
            buy_price = floor_price * (1 - (0.2 * pct_amp / 100.0))
            raw_qty = abs(dto.qty)
            # order
            self._post_order(dto, 
                side="buy", 
                qty=raw_qty, 
                limit_price=buy_price
            )