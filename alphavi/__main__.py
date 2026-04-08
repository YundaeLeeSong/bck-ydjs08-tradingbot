"""
Primary execution script for the alphavi project.

This script acts as the entry point when running the `alphavi` module directly.
It orchestrates the initialization of necessary services and the execution
of the top-level market data loading endpoints.
"""

import sys
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



def test_ftp():
    """
    Main application loop.
    
    Validates environment configurations, triggers market data loading,
    and prints the resulting StockDataTable.
    """
        
    tickers_to_track = ["AAPL"]
    
    # Load the market data table
    data_table = load_market_data(tickers_to_track)
    
    print("\n--- Market Data Summary ---")
    print(data_table)

def test_alpaca():
    """
    Test routine to execute Alpaca endpoints and verify data fetching.
    """
    print("\n--- Running Alpaca API Tests ---")
    from alphavi.alpaca import AlpacaService
    
    try:
        # [Singleton] (3): Initialize the AlpacaService early to validate the API keys.
        service = AlpacaService(debug=True)
        
        print("\n--- Testing get_account_info() ---")
        account_dto = service.get_account_info()
        print(account_dto)
        
        print("\n--- Testing get_orders() ---")
        orders_table = service.get_orders()
        print(orders_table)
        
        
        print("\nGenerating Finance Report...")
        service.report()

        print("\n--- Testing get_tickers() and get_positions() ---")
        service = AlpacaService()
        from alphavi.models import StockDataTable

        print("\nFetching complete StockDataTable with get_positions()...")
        full_table = service.get_positions()
        print(f"Total assets loaded into table: {len(full_table.get_all())}")

        option_tickers = service.get_tickers(["YieldMax", "Option"]) + service.get_tickers(["Roundhill", "WeeklyPay"])
        index_tickers = service.get_tickers(["MicroSectors"], ["Inverse"])

        print(f"Option Tickers ({len(option_tickers)}): {option_tickers}")
        print("\n--- StockDataTable Output (Option Tickers) ---")
        for ticker in option_tickers:
            dto = full_table.get(ticker)
            if dto:
                print(f"{ticker}: shortable={dto.shortable}, fractionable={dto.fractionable}, qty={dto.qty}, price={dto.price}, entry_price={dto.entry_price}, change_today={dto.latestChangePercent}, pnl={dto.pct_profit_and_loss}")

        print(f"\nIndex Tickers ({len(index_tickers)}): {index_tickers}")
        print("\n--- StockDataTable Output (Index Tickers) ---")
        for ticker in index_tickers:
            dto = full_table.get(ticker)
            if dto:
                print(f"{ticker}: shortable={dto.shortable}, fractionable={dto.fractionable}, qty={dto.qty}, price={dto.price}, entry_price={dto.entry_price}, change_today={dto.latestChangePercent}, pnl={dto.pct_profit_and_loss}")

        # Also test with some actual open positions to see position data populated
        print("\n--- Testing get_stock_data() with actual open positions ---")
        positions_data = service.fetch_endpoint("positions")
        if positions_data and isinstance(positions_data, list) and len(positions_data) > 0:
            pos_table = StockDataTable()
            sample_tickers = [p.get("symbol") for p in positions_data[:3] if p.get("symbol")]
            print(f"Sample position tickers: {sample_tickers}")
            for ticker in sample_tickers:
                dto = service.get_stock_data(ticker)
                pos_table.add(dto)
                
            for ticker in sample_tickers:
                dto = pos_table.get(ticker)
                if dto:
                    print(f"{ticker}: shortable={dto.shortable}, fractionable={dto.fractionable}, qty={dto.qty}, price={dto.price}, entry_price={dto.entry_price}, change_today={dto.latestChangePercent}, pnl={dto.pct_profit_and_loss}")
        else:
            print("No open positions found to test position data.")

        print("--- Alpaca API Tests Completed ---")
    except ValueError as e:
        print(f"Error: {e}")
        print("Ensure APCA_API_BASE_URL, APCA_API_KEY, and APCA_API_SECRET_KEY are set.")



def main():
    test_ftp()
    test_alpaca()



if __name__ == "__main__":
    main()
