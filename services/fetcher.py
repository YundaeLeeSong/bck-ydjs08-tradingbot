"""
Data Fetcher Module
===================
Handles the retrieval of historical market data. Isolates yfinance dependencies.
"""
import warnings
import yfinance as yf

# Suppress specific pandas warnings triggered by yfinance
warnings.filterwarnings("ignore", message=".*Timestamp.utcnow is deprecated.*")
warnings.filterwarnings("ignore", category=FutureWarning)

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
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
        return df
    except Exception as e:
        print(f"Failed to fetch data for {symbol}: {e}")
        return None

def fetch_company_info(symbol):
    """
    Fetches basic company information using yfinance.
    
    Args:
        symbol (str): The stock ticker symbol.
        
    Returns:
        dict: A dictionary containing company information.
    """
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info
    except Exception as e:
        print(f"Failed to fetch info for {symbol}: {e}")
        return {}
