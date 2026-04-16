"""
Stock Analysis & Regression Tool v5.0
------------------------------------
1. Main entry point executing high-cohesion logic.
2. Retrieves winner and loser tickers and graphs/tables them.
3. Excludes rich console and delegates everything to files.
"""

import os
from alphavi.services.yfinance_service import YahooFinanceAPI

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

def main():
    """
    Main entry point for the Stock Analysis Tool.
    """
    # Instantiate the dependency
    extractor = YahooFinanceAPI(debug=True)
    
    # -----------------------------------------------------
    # STRATEGY 1: Shorting Data
    # Intent: Look for big gainers (<$100B MCap) to short.
    # -----------------------------------------------------
    winner_tickers = extractor.get_winner_tickers(
        max_mcap=100_000_000_000,
        min_change=15.0
    )
    
    if winner_tickers:
        winners_table = extractor.get_stocks_table(
            tickers=winner_tickers, 
            graph_path="market_report/shorting"
        )
        _logfile("Shorting", winners_table, active_only=False)

    # -----------------------------------------------------
    # STRATEGY 2: Longing Data
    # Intent: Look for big losers (>$100B MCap) to long.
    # -----------------------------------------------------
    loser_tickers = extractor.get_loser_tickers(
        min_mcap=100_000_000_000,
        max_change=-4.5
    )
    
    if loser_tickers:
        losers_table = extractor.get_stocks_table(
            tickers=loser_tickers, 
            graph_path="market_report/longing"
        )
        _logfile("Longing", losers_table, active_only=False)


    # -----------------------------------------------------
    # STRATEGY 3: Test Assets
    # Intent: Record given test assets.
    # -----------------------------------------------------
    test_tickers = ['TSLA', 'IONQ', 'HIMS', 'AMD', 'PSA', 'MAR', 'IGPT', 'SOXX']
    if test_tickers:
        test_table = extractor.get_stocks_table(
            tickers=test_tickers,
            graph_path="market_report/test"
        )
        _logfile("Test", test_table, active_only=False)

if __name__ == "__main__":
    main()
