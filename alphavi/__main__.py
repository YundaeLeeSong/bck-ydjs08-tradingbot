"""
Primary execution script for the alphavi project.

This script acts as the entry point when running the `alphavi` module directly.
It orchestrates the initialization of necessary services and the execution
of the top-level market data loading endpoints.
"""

import sys
import os
# [Facade] (2): Consume the root facade to execute the high-level application flow.
from alphavi import load_market_data
from alphavi.ftp import FMPService
try:
    # [Singleton] (3): Initialize the FMPService early to validate the API key. 
    # Subsequent calls elsewhere will silently reuse this allocated instance.
    FMPService(debug=True)
except ValueError as e:
    print(f"Error: {e}")
    print("Ensure FMP_API_KEY is in your environment or .env file.")
    sys.exit(1)






def _logfile(name: str, table, active_only: bool = True):
    os.makedirs("log", exist_ok=True)
    log_file = os.path.join("log", f"{name.lower().replace(' ', '_')}.json")
    
    if hasattr(table, '_data'):
        import json
        from dataclasses import asdict
        if active_only:
            filtered_data = {k: asdict(v) for k, v in table._data.items() if getattr(v, 'isActive', True)}
        else:
            filtered_data = {k: asdict(v) for k, v in table._data.items()}
        content = json.dumps(filtered_data, indent=2)
    else:
        content = repr(table)
        
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(content)



def test_ftp_data_override_alpaca():
    from alphavi.ftp import FMPService
    from alphavi.alpaca import AlpacaService
    from alphavi.models import StockDataTable
    
    tickers_to_track = ["AAPL"]
    
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


def test_ftp():
    """
    Main application loop.
    
    Validates environment configurations, triggers market data loading,
    and prints the resulting StockDataTable.
    """
        
    tickers_to_track = ["AAPL"]
    
    # Load the market data table
    data_table = load_market_data(tickers_to_track)
    
    _logfile("Market Data Summary", data_table)




def test_alpaca():
    """
    Test routine to execute Alpaca endpoints and verify data fetching.
    """
    from alphavi.alpaca import AlpacaService
    
    try:
        # [Singleton] (3): Initialize the AlpacaService early to validate the API keys.
        service = AlpacaService(debug=True)
        
        account_dto = service.get_account_info()
        _logfile("account_info", account_dto)
        
        orders_table = service.get_orders()
        _logfile("orders", orders_table)
        
        service.report()

        service = AlpacaService()
        from alphavi.models import StockDataTable

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



def main():
    # test_ftp()
    # test_alpaca()
    test_ftp_data_override_alpaca()



if __name__ == "__main__":
    main()
