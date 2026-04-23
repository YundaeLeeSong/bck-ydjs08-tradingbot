"""
Primary execution script for the alphavi project.

This script acts as the entry point when running the `alphavi` module directly.
It orchestrates the initialization of necessary services and the execution
of the top-level market data loading endpoints.
"""

import sys
import os
import math
# [Facade] (2): Consume the root facade to execute the high-level application flow.
from bumblebee.external import FMPService
from bumblebee.external import YFinanceService
from bumblebee.external import AlpacaService
from bumblebee.bot import Bumblebee

try:
    # [Singleton] (3): Initialize the services early to validate the API keys and start debug modes.
    # Subsequent calls elsewhere will silently reuse these allocated instances.
    fmp = FMPService(debug=True)
    yfinance = YFinanceService(debug=True)
    alpaca = AlpacaService(debug=True)
except ValueError as e:
    print(f"Error: {e}")
    print("Ensure all required API keys are in your environment or .env file.")
    sys.exit(1)





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



def test_fmp_data_override_alpaca():
    from bumblebee.external import FMPService
    from bumblebee.external import AlpacaService
    from bumblebee.models import StockDataTable
    
    tickers_to_track = ["AAPL", "MSTR", "TSLA"]
    
    try:
        fmp = FMPService()
        alpaca = AlpacaService()
    except ValueError as e:
        print(f"Error initializing services: {e}")
        return
        
    result_table = StockDataTable()
    table1 = StockDataTable()
    table2 = StockDataTable()
    
    for ticker in tickers_to_track:
        dto1 = fmp.get_stock_data(ticker)
        dto2 = alpaca.get_stock_data(ticker)
        dto_result = dto1.override(dto2)
        result_table.add(dto_result)
        table1.add(dto1)
        table2.add(dto2)
        
    _logfile("Override operand 1", table1)
    _logfile("Override operand 2", table2)
    _logfile("Override Result", result_table)


def test_fmp():
    """
    Main application loop.
    
    Validates environment configurations, triggers market data loading,
    and prints the resulting StockDataTable.
    """
        
    tickers_to_track = ["AAPL"]
    
    # Load the market data table
    data_table = None # load_market_data removed
    
    if data_table:
        _logfile("Market Data Summary", data_table)




def test_alpaca():
    """
    Test routine to execute Alpaca endpoints and verify data fetching.
    """
    from bumblebee.external import AlpacaService
    
    try:
        # [Singleton] (3): Initialize the AlpacaService early to validate the API keys.
        service = AlpacaService()
        
        account_dto = service.get_account_info()
        _logfile("account_info", account_dto)
        # print(f'[DEBUG] test_alpaca: purchasing power is now, ${service.get_unit_value(account_dto):.2f} for rebalance, long: {service.is_long(account_dto)}, short: {service.is_short(account_dto)}')
        
        orders_table = service.get_orders()
        _logfile("orders", orders_table)
        
        service.report()

        from bumblebee.models import StockDataTable

        full_table = service.get_positions()
        _logfile("full_positions", full_table)
        # # debug on console
        # for dto in full_table.get_all():
        #     if (dto.isActive): print(f"{dto.symbol}\t{dto.qty}")



        option_tickers = service.get_tickers(["YieldMax"], ["Short"]) \
        + service.get_tickers(["Roundhill", "WeeklyPay"]) 

        option_table = StockDataTable()
        for t in option_tickers:
            dto = full_table.get(t)
            if dto: option_table.add(dto)
        _logfile("Option Tickers", option_table, active_only=False)
        


        inv_option_tickers = service.get_tickers(["YieldMax", "Short"])
        inv_option_table = StockDataTable()
        for t in inv_option_tickers:
            dto = full_table.get(t)
            if dto: inv_option_table.add(dto)
        _logfile("Option Tickers Inverse", inv_option_table, active_only=False)



        index_tickers = service.get_tickers(["MicroSectors"], ["Inverse", "due"])
        index_table = StockDataTable()
        for t in index_tickers:
            dto = full_table.get(t)
            if dto: index_table.add(dto)
        _logfile("Index Tickers", index_table, active_only=False)
        


        index_tickers_inv = service.get_tickers(["MicroSectors", "Inverse"], ["due"])
        index_table = StockDataTable()
        for t in index_tickers_inv:
            dto = full_table.get(t)
            if dto: index_table.add(dto)
        _logfile("Index Tickers Inverse", index_table, active_only=False)
        
        index_tickers_x2 = service.get_tickers(["Bull", "2X"]) + service.get_tickers(["Leveraged", "2X"], ["Inverse"])
        index_table_x2 = StockDataTable()
        for t in index_tickers_x2:
            dto = full_table.get(t)
            if dto: index_table_x2.add(dto)
        _logfile("Index Tickers x2", index_table_x2, active_only=False)


        index_tickers_x3 = service.get_tickers(["Bull", "3X"]) + service.get_tickers(["Leveraged", "3X"], ["Inverse"])
        index_table_x3 = StockDataTable()
        for t in index_tickers_x3:
            dto = full_table.get(t)
            if dto: index_table_x3.add(dto)
        _logfile("Index Tickers x3", index_table_x3, active_only=False)
        



    except ValueError as e:
        print(f"Error: {e}")
        print("Ensure APCA_API_BASE_URL, APCA_API_KEY, and APCA_API_SECRET_KEY are set.")



def test_yfinance():
    """
    Test routine to execute YFinance endpoints and verify data fetching.
    """
    from bumblebee.external import YFinanceService
    
    try:
        # [Singleton] (3): Initialize the YFinanceService early to test.
        service = YFinanceService(debug=True)
        
        # STRATEGY 1: Shorting Data
        winner_tickers = service.get_winner_tickers(
            max_mcap=100_000_000_000,
            min_change=15.0
        )
        
        if winner_tickers:
            winners_table = service.get_stocks_table(
                tickers=winner_tickers, 
                graph_path="market_report/shorting"
            )
            _logfile("Shorting", winners_table, active_only=False)

        # STRATEGY 2: Longing Data
        loser_tickers = service.get_loser_tickers(
            min_mcap=100_000_000_000,
            max_change=-4.5
        )
        
        if loser_tickers:
            losers_table = service.get_stocks_table(
                tickers=loser_tickers, 
                graph_path="market_report/longing"
            )
            _logfile("Longing", losers_table, active_only=False)

        # STRATEGY 3: Test Assets
        index_tickers = [
            'COIN', 'CONY', 'CONL', # coinbase
            'MSTR', 'MSTY', 'MSTU', 'STRC', 'STRK', 'STRD', 'STRF', # stragegy
            'GDXU', 'SLV','COPX','LIT', # minings
            'SPXL', 'SSO', 'SPY', # essentials
            'TQQQ', 'QLD', 'QQQ', 'QQQM', 'QQQU', # Tech
            'UDOW', 'DDM', 'DIA', # dow johns
            'TNA',  'URTY', 'IWM', # russell 2000
            'JEPI', 'JEPQ', 'SCHD', # accumulative assets
            'GBTC', 'BTC', 'ETHE', 'ETH', # crypto
            'AIQ', 'UFO', 'QTUM', # future
            'BUG', 'CHAT', 'IGV', 'IGPT', 'AOTS', # software
            'WEBL', 'SOXX', # Hardware
        ]
        if index_tickers:
            test_table = service.get_stocks_table(
                tickers=index_tickers,
                graph_path="market_report/index"
            )
            _logfile("index", test_table, active_only=False)
            
    except Exception as e:
        print(f"Error in test_yfinance: {e}")

def test_fmp_data_override_yfinance_override_alpaca():
    from bumblebee.external import FMPService
    from bumblebee.external import YFinanceService
    from bumblebee.external import AlpacaService
    from bumblebee.models import StockDataTable
    
    tickers_to_track = ["AAPL", "MSTR", "TSLA"]
    
    
    result_table = StockDataTable()
    table_fmp = StockDataTable()
    table_yfinance = StockDataTable()
    table_alpaca = StockDataTable()
    
    for ticker in tickers_to_track:
        table_fmp.add(fmp.get_stock_data(ticker))
        table_yfinance.add(yfinance.get_stock_data(ticker))
        table_alpaca.add(alpaca.get_stock_data(ticker))
        
    result_table = table_fmp.override(table_yfinance).override(table_alpaca)

    for dto in result_table.get_all(active_only=True):
        print(repr(dto))
        
    _logfile("Override operand 1 FMP", table_fmp)
    _logfile("Override operand 2 YFinance", table_yfinance)
    _logfile("Override operand 3 Alpaca", table_alpaca)
    _logfile("Override Result FMP_YFinance_Alpaca", result_table)


def test_orders():
    """
    Test routine to execute Alpaca endpoints for creating and canceling orders.
    """
    from bumblebee.external import FMPService
    from bumblebee.external import YFinanceService
    from bumblebee.external import AlpacaService
    
    try:
        yfinance = YFinanceService()
        alpaca = AlpacaService()
        
        # We will test using AAPL and NVDA. Ensure we have their full DTOs
        # 1. Fetch from all sources
        aapl_yf = yfinance.get_stock_data("AAPL")
        aapl_alpaca = alpaca.get_stock_data("AAPL")

        nvda_yf = yfinance.get_stock_data("NVDA")
        nvda_alpaca = alpaca.get_stock_data("NVDA")

        # 2. Override FMP -> YFinance -> Alpaca to get the final unified DTO
        aapl_dto = aapl_yf.override(aapl_alpaca)
        nvda_dto = nvda_yf.override(nvda_alpaca)
        short_ticker = 'CAR'
        short_dto = \
            yfinance.get_stock_data(short_ticker)\
            .override(alpaca.get_stock_data(short_ticker))

        print("\n--- [TEST] POSTING ORDERS ---")
        
        # Test 1: Buy AAPL (fractionable handling check)
        # Use Standard Deviation (SD) to lower the buy limit price
        aapl_buy_price = aapl_dto.rt_price * (1 - (aapl_dto.pct_sd / 100))
        print(f"Testing POST buy for AAPL (qty: 0.123, limit: {aapl_buy_price:.2f} based on SD: {aapl_dto.pct_sd}%)")
        alpaca.post_order(aapl_dto, side="buy", qty=aapl_dto.qty * 2, limit_price=aapl_buy_price)

        # Test 2: Sell NVDA
        # Use Standard Deviation (SD) to raise the sell limit price
        nvda_sell_price = nvda_dto.rt_price * (1 + (nvda_dto.pct_sd / 100))
        print(f"Testing POST sell for NVDA (qty: 1.5, limit: {nvda_sell_price:.2f} based on SD: {nvda_dto.pct_sd}%)")
        alpaca.post_order(nvda_dto, side="sell", qty=nvda_dto.qty - 0.01, limit_price=nvda_sell_price)


        sell_price = short_dto.price * (1 + (short_dto.pct_sd / 100))
        print(f"Testing POST sell for ***** limit: {sell_price:.2f} based on SD: {short_dto.pct_sd}%)")
        alpaca.post_order(short_dto, side="sell", qty=100, limit_price=sell_price)

        

        print("\n--- [TEST] FETCHING ACTIVE ORDERS ---")
        orders_table = alpaca.get_orders()
        _logfile("orders_post_test", orders_table)
        print(f"Active orders found: {len(orders_table.get_all())}")
        for order in orders_table.get_all():
            print(f"  {order.symbol}: {order.side} {order.qty} @ ${order.limit_price} (ID: {order.id})")

        # print("\n--- [TEST] DELETING ORDERS ---")
        # # Test 3: Delete AAPL and NVDA orders
        # print("Testing delete_all_orders (Clears everything)")
        # alpaca.delete_all_orders()

        # print("\n--- [TEST] VERIFYING DELETIONS ---")
        # orders_table_after = alpaca.get_orders()
        # _logfile("orders_after_delete_test", orders_table_after)
        # print(f"Active orders found after deletion: {len(orders_table_after.get_all())}")

    except Exception as e:
        print(f"Error in test_orders: {e}")








def main():
    # test_fmp()
    # test_alpaca()
    # test_fmp_data_override_alpaca()
    test_yfinance()
    # test_fmp_data_override_yfinance_override_alpaca()
    # test_orders()

    print(f"\n--- Starting Trading Bot: {__name__} ---")
    
    # Instantiate Bumblebee
    bot = Bumblebee(name=__name__)
    bot.rebalance("long", "soft")

if __name__ == "__main__":
    main()
