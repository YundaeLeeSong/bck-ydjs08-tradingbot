"""
Stock Analysis & Regression Tool v5.0
------------------------------------
1. Logic: High cohesion logic is set in main.py, making constraints explicit.
2. Screens for both Longing (Losers) and Shorting (Gainers) candidates.
3. Delegates fetching and plotting to domain packages dynamically.
"""

from rich.console import Console
from services.screener import get_filtered_movers
from services.fetcher import fetch_historical_data, fetch_company_info
from services.analyzer import analyze_stock_data
from core.models import AnalysisSession, TickerRuntimeData
from views.plotter import generate_all_plots
from views.cli import display_summary_table

def run_analysis_pipeline(name, screener_id, output_dir, **constraints):
    """
    Executes the analysis pipeline for a specific trading strategy (e.g., Longing, Shorting).
    All dependencies and constraints are injected from here.
    """
    console = Console()
    console.print(f"\n[bold blue][{name.upper()} STRATEGY][/bold blue] Initiating Market Scan...")
    
    session = AnalysisSession(name=name)
    
    # 1. SCREENING: Fetch data based on explicit constraints passed from main()
    stocks = get_filtered_movers(screener_id=screener_id, **constraints)
    
    if not stocks:
        console.print(f"No stocks matched the criteria for {name} today.")
        return

    console.print(f"Found {len(stocks)} candidates. Starting analysis...")
    
    for s in stocks:
        symbol = s['ticker']
        console.print(f"Graphing {symbol} (1Y Data)...")
        
        # 2. DATA SOURCING: Fetch historical data and metadata
        df = fetch_historical_data(symbol)
        info = fetch_company_info(symbol)
        
        # Initialize runtime data model
        model = TickerRuntimeData(
            ticker=symbol,
            price=s['price'],
            change_pct=s['change'],
            volume=s['volume'],
            market_cap=s['mcap'],
            sector=info.get('sector', 'N/A')
        )
        
        if df is not None and not df.empty:
            # 3. ANALYSIS: Calculate statistical and mathematical metrics
            metrics = analyze_stock_data(df)
            
            # Update Model with calculated metrics
            model.r_squared = metrics.get('r_squared')
            model.slope = metrics.get('slope')
            model.num_zero_crossings = metrics.get('num_zeros')
            model.mad = metrics.get('mad')
            model.sd = metrics.get('sd')
            
            # 4. PRESENTATION: Generate visual graphs
            generate_all_plots(symbol, df, metrics, output_dir=output_dir)
                
        session.add_result(model)
            
    console.print(f"Analysis complete. All graphs saved to {output_dir}\n")

    # Display Summary Table using session models
    display_summary_table(name, session)


def main():
    """
    Main entry point for the Stock Analysis Tool.
    """
    # Pattern: Dependency Injection - Defines strategies explicitly using dependency injection to reduce coupling.
    # -----------------------------------------------------
    # STRATEGY 1: Shorting Data
    # Intent: Look for big gainers (>$1B MCap) to short.
    # -----------------------------------------------------
    run_analysis_pipeline(
        name="Shorting",
        screener_id="day_gainers",
        output_dir="_data/shorting",
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
        output_dir="_data/longing",
        min_mcap=100_000_000_000,
        min_price=10.0,
        max_change=-3.5
    )

if __name__ == "__main__":
    main()