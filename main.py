"""
Stock Analysis & Regression Tool v5.0
------------------------------------
1. Logic: High cohesion logic is set in main.py, making constraints explicit.
2. Screens for both Longing (Losers) and Shorting (Gainers) candidates.
3. Delegates fetching and plotting to stock_analysis package dynamically.
"""

from stock_analysis import get_filtered_movers, fetch_historical_data, generate_all_plots

def run_analysis_pipeline(name, screener_id, output_dir, **constraints):
    """
    Executes the analysis pipeline for a specific trading strategy (e.g., Longing, Shorting).
    All dependencies and constraints are injected from here.
    """
    print(f"\n[{name.upper()} STRATEGY] Initiating Market Scan...")
    
    # Fetch data based on explicit constraints passed from main()
    stocks = get_filtered_movers(screener_id=screener_id, **constraints)
    
    if not stocks:
        print(f"No stocks matched the criteria for {name} today.")
        return

    print(f"Found {len(stocks)} candidates. Starting analysis...")
    
    for s in stocks:
        symbol = s['ticker']
        print(f"Graphing {symbol} (1Y Data)...")
        
        df = fetch_historical_data(symbol)
        if df is not None and not df.empty:
            generate_all_plots(symbol, df, output_dir=output_dir)
            
    print(f"Analysis complete. All graphs saved to {output_dir}\n")

    # Display Summary Table
    print(f"--- {name.upper()} SUMMARY ---")
    header = f"{'Ticker':<10} | {'Price':<10} | {'% Change':<10} | {'Volume':<12} | {'Market Cap':<12}"
    print(header)
    print("-" * len(header))
    
    for s in stocks:
        mcap_billions = s['mcap'] / 1_000_000_000
        vol_millions = s['volume'] / 1_000_000
        print(f"{s['ticker']:<10} | "
              f"{s['price']:<10.2f} | "
              f"{s['change']:>8.2f}% | "
              f"{vol_millions:>10.2f}M | "
              f"{mcap_billions:>10.2f}B")

def main():
    """
    Main entry point for the Stock Analysis Tool.
    Defines strategies explicitly using dependency injection to reduce coupling.
    """
    # -----------------------------------------------------
    # STRATEGY 1: Shorting Data
    # Intent: Look for big gainers (>$1B MCap) to short.
    # -----------------------------------------------------
    run_analysis_pipeline(
        name="Shorting",
        screener_id="day_gainers",
        output_dir="./shorting_data",
        min_mcap=1_000_000_000,
        min_price=10.0,
        min_change=10.0
    )

    # -----------------------------------------------------
    # STRATEGY 2: Longing Data
    # Intent: Look for big losers (>$100B MCap) to long.
    # -----------------------------------------------------
    run_analysis_pipeline(
        name="Longing",
        screener_id="day_losers",
        output_dir="./longing_data",
        min_mcap=100_000_000_000,
        min_price=10.0,
        max_change=-7.0
    )

if __name__ == "__main__":
    main()
