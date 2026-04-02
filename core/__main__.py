"""
Stock Analysis & Regression Tool v5.0
------------------------------------
1. Logic: High cohesion logic is set in main.py, making constraints explicit.
2. Screens for both Longing (Losers) and Shorting (Gainers) candidates.
3. Delegates fetching and plotting to domain packages dynamically.
"""

from rich.console import Console
from services.yahoo_finance_api import YahooFinanceAPI
from services.analysis import analyze_stock_data
from core.analysis_report import AnalysisReport
from core.stock_metrics import StockMetrics
from views.visualization import generate_all_plots
from views.console import display_summary_table

def run_analysis_pipeline(name, extractor, screener_id, output_dir, **constraints):
    """
    Executes the analysis pipeline for a specific trading strategy (e.g., Longing, Shorting).
    All dependencies and constraints are injected from here.
    
    Args:
        name (str): The name of the trading strategy.
        extractor (MarketDataAPI): The data extraction service instance.
        screener_id (str): The predefined screener identifier.
        output_dir (str): The directory to save generated plots to.
        **constraints: The constraints to filter screener candidates.
        
    Returns:
        None
    """
    console = Console()
    console.print(f"\n[bold blue][{name.upper()} STRATEGY][/bold blue] Initiating Market Scan...")
    
    session = AnalysisReport(name=name)
    
    # [Template Method Pattern] (1): SCREENING - Fetch data based on explicit constraints passed from main()
    stocks = extractor.fetch_movers(screener_id=screener_id, **constraints)
    
    if not stocks:
        console.print(f"No stocks matched the criteria for {name} today.")
        return

    console.print(f"Found {len(stocks)} candidates. Starting analysis...")
    
    for s in stocks:
        symbol = s['ticker']
        short_name = s.get('name', '')
        console.print(f"Graphing {symbol} (1Y Data)...")
        
        # [Template Method Pattern] (2): DATA SOURCING - Fetch historical data and metadata via Extractor
        df = extractor.fetch_historical_data(symbol)
        info = extractor.fetch_company_info(symbol)
        
        company_name = info.get('shortName', short_name) or info.get('longName', '')
        
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        if sector == 'N/A' and industry == 'N/A':
            sector_industry = 'N/A'
        elif sector != 'N/A' and industry != 'N/A':
            sector_industry = f"{sector} / {industry}"
        else:
            sector_industry = sector if sector != 'N/A' else industry
            
        model = StockMetrics(
            ticker=symbol,
            price=s['price'],
            change_pct_daily=s['change'],
            volume=s['volume'],
            market_cap=s['mcap'],
            sector_industry=sector_industry,
            company_name=company_name
        )
        
        if df is not None and not df.empty:
            # [Template Method Pattern] (3): ANALYSIS - Calculate statistical and mathematical metrics
            metrics = analyze_stock_data(df)
            
            model.r_squared = metrics.get('r_squared')
            model.slope = metrics.get('slope')
            model.num_zero_crossings = metrics.get('num_zeros')
            model.mad = metrics.get('mad')
            model.sd = metrics.get('sd')
            
            # [Template Method Pattern] (4): PRESENTATION - Generate visual graphs
            generate_all_plots(symbol, df, metrics, output_dir=output_dir)
                
        session.add_result(model)
        console.print(f"[dim]Debug Model:[/dim]\n{repr(model)}")
            
    console.print(f"Analysis complete. All graphs saved to {output_dir}\n")
    console.print(f"[dim]Debug Session:[/dim]\n{repr(session)}\n")

    display_summary_table(name, session)

def run_company_search_pipeline(name, extractor, company_query, output_dir):
    """
    Executes the analysis pipeline to fetch all tickers related to a specific company name.
    
    Args:
        name (str): The name of the custom search strategy.
        extractor (MarketDataAPI): The data extraction service instance.
        company_query (str): The company name to search for.
        output_dir (str): The directory to save generated plots to.
        
    Returns:
        None
    """
    console = Console()
    console.print(f"\n[bold yellow][{name.upper()} SEARCH][/bold yellow] Initiating Query for '{company_query}'...")
    
    session = AnalysisReport(name=name)
    
    # [Template Method Pattern] (1): SCREENING - Search for tickers by company name
    stocks = extractor.search_by_name(query=company_query)
    
    if not stocks:
        console.print(f"No stocks matched the company name '{company_query}' today.")
        return

    console.print(f"Found {len(stocks)} candidates. Starting analysis...")
    
    for s in stocks:
        symbol = s['ticker']
        console.print(f"Graphing {symbol} (1Y Data)...")
        
        # [Template Method Pattern] (2): DATA SOURCING - Fetch historical data and metadata via Extractor
        df = extractor.fetch_historical_data(symbol)
        info = extractor.fetch_company_info(symbol)
        
        # Extract live values from info since search doesn't provide them
        price = info.get('currentPrice', info.get('regularMarketPrice', 0.0))
        change_pct = info.get('regularMarketChangePercent', 0.0)
        volume = info.get('volume', info.get('regularMarketVolume', 0))
        mcap = info.get('marketCap', 0)
        company_name = info.get('shortName', s.get('name', '')) or info.get('longName', '')
        
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        if sector == 'N/A' and industry == 'N/A':
            sector_industry = 'N/A'
        elif sector != 'N/A' and industry != 'N/A':
            sector_industry = f"{sector} / {industry}"
        else:
            sector_industry = sector if sector != 'N/A' else industry
        
        model = StockMetrics(
            ticker=symbol,
            price=price,
            change_pct_daily=change_pct,
            volume=volume,
            market_cap=mcap,
            sector_industry=sector_industry,
            company_name=company_name
        )
        
        if df is not None and not df.empty:
            # [Template Method Pattern] (3): ANALYSIS - Calculate statistical and mathematical metrics
            metrics = analyze_stock_data(df)
            
            model.r_squared = metrics.get('r_squared')
            model.slope = metrics.get('slope')
            model.num_zero_crossings = metrics.get('num_zeros')
            model.mad = metrics.get('mad')
            model.sd = metrics.get('sd')
            
            # [Template Method Pattern] (4): PRESENTATION - Generate visual graphs
            generate_all_plots(symbol, df, metrics, output_dir=output_dir)
                
        session.add_result(model)
        console.print(f"[dim]Debug Model:[/dim]\n{repr(model)}")
            
    console.print(f"Analysis complete. All graphs saved to {output_dir}\n")
    console.print(f"[dim]Debug Session:[/dim]\n{repr(session)}\n")

    display_summary_table(name, session)


def main():
    """
    Main entry point for the Stock Analysis Tool.
    """
    extractor = YahooFinanceAPI(debug=True)
    
    # [Dependency Injection]: Defines strategies explicitly using dependency injection to reduce coupling.
    # -----------------------------------------------------
    # STRATEGY 1: Shorting Data
    # Intent: Look for big gainers (>$1B MCap) to short.
    # -----------------------------------------------------
    run_analysis_pipeline(
        name="Shorting",
        extractor=extractor,
        screener_id="day_gainers",
        output_dir="_data/shorting",
        min_mcap=1_000_000_000,
        min_price=10.0,
        min_change=15.0
    )

    # -----------------------------------------------------
    # STRATEGY 2: Longing Data
    # Intent: Look for big losers (>$100B MCap) to long.
    # -----------------------------------------------------
    run_analysis_pipeline(
        name="Longing",
        extractor=extractor,
        screener_id="day_losers",
        output_dir="_data/longing",
        min_mcap=100_000_000_000,
        min_price=10.0,
        max_change=-3.5
    )

    # -----------------------------------------------------
    # STRATEGY 3: Company Search (YieldMax)
    # Intent: Look up all tickers related to a specific company name.
    # -----------------------------------------------------
    run_company_search_pipeline(
        name="YieldMax Portfolio",
        extractor=extractor,
        company_query="yieldmax",
        output_dir="_data/yieldmax"
    )



    run_company_search_pipeline(
        name="Roundhill Portfolio",
        extractor=extractor,
        company_query="WeeklyPay",
        output_dir="_data/roundhill"
    )

if __name__ == "__main__":
    main()
