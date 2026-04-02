"""
Data Fetcher Module
===================
Handles the retrieval of historical market data. Isolates yfinance dependencies.
"""
import yfinance as yf

def fetch_historical_data(symbol, period="1y", interval="1d"):
    """
    Fetches historical stock data using yfinance.
    
    Args:
        symbol (str): The stock ticker symbol.
        period (str): The time period to fetch data for. Default is "1y".
        interval (str): The interval of the data. Default is "1d".
        
    Returns:
        pandas.DataFrame: The historical data.
    """
    # Pattern: Facade (1) - We wrap the complex yfinance library behind a simple interface.
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        return df
    except Exception as e:
        print(f"Failed to fetch data for {symbol}: {e}")
        return None
