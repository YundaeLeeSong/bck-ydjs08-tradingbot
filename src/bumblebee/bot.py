"""
Framework module for the alphavi project.

Provides the base trading framework that defines the skeleton of the trading
strategy, deferring specific implementation steps to subclasses.
"""

from typing import List, Optional
import json
import glob
import os
import shutil
from datetime import datetime
from dataclasses import asdict
from ydjs_util.core import get_env_var, get_env_arr, get_resource
from bumblebee.external.gmail_service import GmailService
from bumblebee.external import AlpacaService
from bumblebee.external import YFinanceService
from bumblebee.models import AccountDTO, ActiveOrderTable, StockDataTable

def _logfile(name: str, table, active_only: bool = True):
    os.makedirs("log", exist_ok=True)
    log_file = os.path.join("log", f"{name.lower().replace(' ', '_')}.json")
    
    if hasattr(table, 'get_all'):
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
        self.is_euporia: bool = False
        self.is_expansion: bool = False
        self.is_ressession: bool = False
        self.is_depression: bool = False
        self.is_long: bool = AlpacaService().is_long(self.account_dto)
        self.is_short: bool = AlpacaService().is_short(self.account_dto)

        self.position_tickers: List[str] = self._positions.get_tickers(active_only=True)

        self.option_tickers: List[str] = (
            AlpacaService().get_tickers(["YieldMax"], ["Short"]) + 
            AlpacaService().get_tickers(["Roundhill", "WeeklyPay"]) +
            AlpacaService().get_tickers(["Bitwise", "Option Income Strategy"]) +
            AlpacaService().get_tickers(["Kurv", "Yield"]) +
            AlpacaService().get_tickers(["REX", "Equity Premium Income"]) +
            AlpacaService().get_tickers(["Defiance", "Income Target"]) +
            AlpacaService().get_tickers(["GraniteShares", "YieldBOOST"]) 
        )
        self.option_tickers_inv: List[str] = AlpacaService().get_tickers(["YieldMax", "Short"])



        self.market_index_tickers: List[str] = get_env_arr("INDICES")
        self.leverage_tickers: List[str] = get_env_arr("LEVERAGES")
        self.large_cap_tickers = self.market_index_tickers + YFinanceService().get_etf_holdings(
            self.market_index_tickers, 
            min_mcap=50_000_000_000
        )
        self.small_cap_tickers = YFinanceService().get_etf_holdings(
            self.market_index_tickers, 
            max_mcap=50_000_000_000
        )

        # self.index_tickers: List[str] = AlpacaService().get_tickers(["MicroSectors"], ["Inverse", "due"])

        # self.index_tickers_x2: List[str] = (
        #     AlpacaService().get_tickers(["Bull", "2X"]) + 
        #     AlpacaService().get_tickers(["Leveraged", "2X"], ["Inverse"])
        # )

        # self.index_tickers_x3: List[str] = (
        #     AlpacaService().get_tickers(["Bull", "3X"]) + 
        #     AlpacaService().get_tickers(["Leveraged", "3X"], ["Inverse"])
        # )

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
        self.active_long_positions: StockDataTable = yfinance_table.override(self._positions).filter_active()
        
        yfinance_positions_table = YFinanceService().get_stocks_table(self.position_tickers)
        self.active_positions: StockDataTable = yfinance_positions_table.override(self._positions).filter_active()
        
        _logfile("positions", self._positions, active_only=False)
        _logfile("positions (actives)", self._positions)
        _logfile("active positions", self.active_positions, active_only=False)
        _logfile("active long positions", self.active_long_positions, active_only=False)
        _logfile("account info", self.account_dto)

        


        self._report_state()

    def _report_state(self) -> None:
        """
        Reports the instance variables value on console.
        """
        print("\n" + "="*60)
        print(" TRADING FRAMEWORK INITIALIZATION REPORT")
        print("="*60)
        print(f"[Account] Unit Value:             ${self.unit_value:.2f}")
        print(f"[Account] Is Entry:               {self.is_entry}")
        print(f"[Account] Is Euporia:             {self.is_euporia}")
        print(f"[Account] Is Expansion:           {self.is_expansion}")
        print(f"[Account] Is Ressession:          {self.is_ressession}")
        print(f"[Account] Is Depression:          {self.is_depression}")
        print(f"[Account] Is Long:                {self.is_long}")
        print(f"[Account] Is Short:               {self.is_short}")
        print(f"[Account] Open Orders:            {len(self.orders_table)}")
        print(f"[Account] daily % equity change:  {self.account_dto.pct_equity_change} %")
        print(f"[Data] Position Tickers Amount: {len(self.active_positions)}")
        print(f"[Data] Option Tickers:          {self.option_tickers}")
        print(f"[Data] Option Tickers Inv:      {self.option_tickers_inv}")
        print(f"[Data] Market Index Tickers:    {self.market_index_tickers}")
        print(f"[Data] Leverage Tickers:        {self.leverage_tickers}")
        print(f"[Data] Large Cap Tickers:       {self.large_cap_tickers}")
        print(f"[Data] Small Cap Tickers:       {self.small_cap_tickers}")
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

    def report_email(self) -> None:
        """Emails market reports based on a template and generated graph attachments."""
        non_interactive = get_env_var("EMAIL_NONINTERACTIVE")
        if non_interactive and non_interactive.lower() in ("true", "1", "yes"):
            print("Email sending skipped due to EMAIL_NONINTERACTIVE flag.")
            return

        recipients = get_env_arr("RECIPIENTS")
        if not recipients:
            print("No recipients configured. Skipping email report.")
            return

        template_path = get_resource("market_report_template.html")
        if not template_path:
            print("Could not locate market_report_template.html. Skipping email report.")
            return

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except Exception as e:
            print(f"Error reading template: {e}")
            return

        # Inject date
        current_time = datetime.now()
        current_date_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        subject_date_str = current_time.strftime("[%Y/%m/%d]")
        base_html = html_content.replace("{date}", current_date_str)

        def _send_report(report_type: str, paths: List[str], desc_html: str):
            attachments = []
            for path in paths:
                attachments.extend(glob.glob(path))
            
            if not attachments:
                print(f"No attachments found for {report_type}. Skipping email.")
                return

            body_html = base_html.replace("{report_type}", report_type).replace("{description}", desc_html)

            print(f"Sending {report_type} market report email to {len(recipients)} recipients with {len(attachments)} attachments...")
            success, err = GmailService().send_email(
                recipients=recipients,
                subject=f"{subject_date_str} Market Report ({report_type})",
                body_html=body_html,
                attachments=attachments
            )
            if success:
                print(f"{report_type} email sent successfully.")
            else:
                print(f"Failed to send {report_type} email: {err}")

        # Send Shorting report
        _send_report("Shorting", ["market_report/shorting/*.png"], "<strong>Shorting:</strong> Focus on short position opportunities (small-cap, higher price).")
        
        # Send Longing report
        _send_report("Longing", ["market_report/longing/*.png"], "<strong>Longing:</strong> Focus on long position opportunities (large-cap (including M7), lower price).")

        # Cleanup
        shutil.rmtree("market_report", ignore_errors=True)

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
        for dto in self.active_long_positions:
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            # qty validate
            if dto.qty < 0:
                print(f"[PASS] {dto.symbol}: Short position.")
                continue # short position
            
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price) if p > 0]
            if not available_prices:
                print(f"[PASS] {dto.symbol}: No price data available.")
                continue # no price data
            floor_price = min(available_prices)
            ceil_price = max(available_prices)
            if 4 * self.unit_value < floor_price:
                print(f"[PASS] {dto.symbol}: Overpriced relative to account.")
                continue # overpriced relative to account
            ##################################################################
            ###### LOGIC
            ##################################################################
            if (pct_amp > 10.0 and dto.pct_net_pnl < -3.0 * pct_amp): # big lost/gained tickers
                notional_value = self.unit_value / 4 
                # **Notional Value: the total value of the underlying asset in a contract
                buy_price = floor_price * (1 - (0.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            elif (dto.pct_net_pnl < -10.0 * pct_amp): # big lost/gained tickers
                notional_value = self.unit_value / 4
                buy_price = floor_price * (1 - (1.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            elif (4 * pct_amp < dto.pct_net_pnl):
                notional_value = self.unit_value / 4
                buy_price = floor_price * (1 - (1.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            elif (dto.qty == 0.01): # tickers to new entry
                notional_value = self.unit_value / 7
                buy_price = floor_price * (1 - (0.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            elif (dto.qty == 0):
                notional_value = self.unit_value / 7
                buy_price = floor_price * (1 - (0.5 * pct_amp / 100.0))
                raw_qty = notional_value / buy_price
            else:
                print(f"[PASS] {dto.symbol}: Did not meet soft rebalance long criteria.")
                continue 
            # calculation, constant notional value, consistent buying
            # order
            print(f"[ACTION] Soft Rebalance Long: {dto.symbol} | Buy Price: {buy_price:.2f} | Qty: {raw_qty:.4f}")
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
        for dto in self.active_positions:
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            if (dto.pct_net_pnl <= 0):
                print(f"[PASS] {dto.symbol}: PNL <= 0.")
                continue
            # qty validate
            if dto.qty <= 0.01:
                print(f"[PASS] {dto.symbol}: qty <= 0.01.")
                continue
            
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price, dto.entry_price) if p > 0]
            if not available_prices:
                print(f"[PASS] {dto.symbol}: No price data available.")
                continue # no price data
            floor_price = min(available_prices)
            ceil_price = max(available_prices)
            # weight validate
            if abs(dto.qty) * ceil_price <= self.unit_value / 2:
                print(f"[PASS] {dto.symbol}: Total value <= unit_value.")
                continue
            ##################################################################
            ###### LOGIC
            ##################################################################
            sell_price = ceil_price * (1 + (0.33 * pct_amp / 100.0))
            raw_qty = abs(dto.qty) - 0.01
            # order
            self._post_order(dto, 
                side="sell", 
                qty=raw_qty, 
                limit_price=sell_price
            )

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
        for dto in self.active_positions:
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            if (dto.pct_net_pnl < 2.0 * pct_amp):
                print(f"[PASS] {dto.symbol}: PNL < 2.0 * pct_amp.")
                continue
            # qty validate
            if dto.qty <= 0.01:
                print(f"[PASS] {dto.symbol}: qty <= 0.01.")
                continue
            
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price, dto.entry_price) if p > 0]
            if not available_prices:
                print(f"[PASS] {dto.symbol}: No price data available.")
                continue # no price data
            floor_price = min(available_prices)
            ceil_price = max(available_prices)
            # weight validate
            if abs(dto.qty) * ceil_price <= self.unit_value:
                print(f"[PASS] {dto.symbol}: Total value <= unit_value.")
                continue
            ##################################################################
            ###### LOGIC
            ##################################################################
            sell_price = ceil_price * (1 + (1.0 * pct_amp / 100.0))
            raw_qty = abs(dto.qty) - 0.01
            # order
            self._post_order(dto, 
                side="sell", 
                qty=raw_qty, 
                limit_price=sell_price
            )

    def _close_short(self) -> None:
        """Executes logic for closing short positions."""
        for dto in self.active_positions:
            # % profit validate
            pct_amp = max(dto.pct_sd, dto.pct_mad)
            if (dto.pct_net_pnl < 0.5 * pct_amp):
                print(f"[PASS] {dto.symbol}: PNL < 0.5 * pct_amp.")
                continue
            # qty validate
            if dto.qty > 0:
                print(f"[PASS] {dto.symbol}: Not a short position.")
                continue
            
            # price validate
            available_prices = [p for p in (dto.rt_price, dto.price, dto.entry_price) if p > 0]
            if not available_prices:
                print(f"[PASS] {dto.symbol}: No price data available.")
                continue # no price data
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