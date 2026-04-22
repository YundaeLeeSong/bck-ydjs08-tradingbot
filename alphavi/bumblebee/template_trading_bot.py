"""
Framework module for the alphavi project.

Provides the base trading framework that defines the skeleton of the trading
strategy, deferring specific implementation steps to subclasses.
"""

from typing import List, Optional
from alphavi.bumblebee.external import AlpacaService
from alphavi.bumblebee.external import YFinanceService
from alphavi.models import AccountDTO, ActiveOrderTable

class TemplateTradingBot:
    """
    Base class for trading strategy execution.
    """
    
    def __init__(self, alpaca_service: Optional[AlpacaService] = None, yfinance_service: Optional[YFinanceService] = None):
        """
        Initializes the framework with required API services and fetches initial state.
        
        Args:
            alpaca_service (Optional[AlpacaService]): The instantiated Alpaca API service. If None, retrieves the Singleton instance.
            yfinance_service (Optional[YFinanceService]): The instantiated Yahoo Finance API service. If None, retrieves the Singleton instance.
        """
        # [Singleton] (3): Invoke instance method to retrieve the single instance if not provided explicitly.
        self.alpaca = alpaca_service or AlpacaService()
        self.yfinance = yfinance_service or YFinanceService()

        self.account_dto: AccountDTO = self.alpaca.get_account_info()
        self.orders_table: ActiveOrderTable = self.alpaca.get_orders()

        self.unit_value: float = self.alpaca.get_unit_value(self.account_dto)
        self.is_entry: bool = self.alpaca.is_entry(self.account_dto)
        self.is_long: bool = self.alpaca.is_long(self.account_dto)
        self.is_short: bool = self.alpaca.is_short(self.account_dto)

        self.option_tickers: List[str] = (
            self.alpaca.get_tickers(["YieldMax"], ["Short"]) + 
            self.alpaca.get_tickers(["Roundhill", "WeeklyPay"])
        )
        self.option_tickers_inv: List[str] = self.alpaca.get_tickers(["YieldMax", "Short"])

        self.index_tickers: List[str] = self.alpaca.get_tickers(["MicroSectors"], ["Inverse", "due"])

        self.index_tickers_x2: List[str] = (
            self.alpaca.get_tickers(["Bull", "2X"]) + 
            self.alpaca.get_tickers(["Leveraged", "2X"], ["Inverse"])
        )

        self.index_tickers_x3: List[str] = (
            self.alpaca.get_tickers(["Bull", "3X"]) + 
            self.alpaca.get_tickers(["Leveraged", "3X"], ["Inverse"])
        )

        self.winning_tickers_to_short: List[str] = self.yfinance.get_winner_tickers(
            max_mcap=100_000_000_000,
            min_change=15.0
        )

        self.loser_tickers_to_long: List[str] = self.yfinance.get_loser_tickers(
            min_mcap=100_000_000_000,
            max_change=-4.5
        )

        self._report_state()

    def _report_state(self) -> None:
        """
        Reports the instance variables value on console.
        """
        print("\n" + "="*60)
        print(" TRADING FRAMEWORK INITIALIZATION REPORT")
        print("="*60)
        print(f"[Account] Unit Value:        ${self.unit_value:.2f}")
        print(f"[Account] Is Entry:          {self.is_entry}")
        print(f"[Account] Is Long:           {self.is_long}")
        print(f"[Account] Is Short:          {self.is_short}")
        print(f"[Account] Active Orders:     {len(self.orders_table.get_all())}")
        print(f"[Data] Option Tickers:       {self.option_tickers}")
        print(f"[Data] Option Tickers Inv:   {self.option_tickers_inv}")
        print(f"[Data] Index Tickers:        {self.index_tickers}")
        print(f"[Data] Index Tickers x2:     {self.index_tickers_x2}")
        print(f"[Data] Index Tickers x3:     {self.index_tickers_x3}")
        print(f"[Data] Winning Tickers (Short): {self.winning_tickers_to_short}")
        print(f"[Data] Loser Tickers (Long):    {self.loser_tickers_to_long}")
        print("="*60 + "\n")

    def execute(self) -> None:
        """
        Executes the overall trading algorithmic sequence.
        """
        # [TemplateMethod] (1): Define the skeleton of the algorithm, invoking deferred logic.
        self._initialize()
        self._stock_up_long()
        self._rebalance_long()
        self._liquidate_long()
        self._stock_up_short()
        self._rebalance_short()
        self._close_short()

    # [TemplateMethod] (2): Primitive operations to be implemented by concrete subclasses.
    def _initialize(self) -> None:
        """Executes initialization steps for the trading strategy."""
        pass

    def _stock_up_long(self) -> None:
        """Executes logic for stocking up long positions."""
        pass

    def _rebalance_long(self) -> None:
        """Executes logic for rebalancing long positions."""
        pass

    def _liquidate_long(self) -> None:
        """Executes logic for liquidating long positions."""
        pass

    def _stock_up_short(self) -> None:
        """Executes logic for stocking up short positions."""
        pass

    def _rebalance_short(self) -> None:
        """Executes logic for rebalancing short positions."""
        pass

    def _close_short(self) -> None:
        """Executes logic for closing short positions."""
        pass
