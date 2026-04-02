"""
Market Data API Module
======================
Defines the standard interface for extracting market data.
"""
from abc import ABC, abstractmethod

# [Strategy Pattern]: Abstract interface for the Extract phase of ETL.
class MarketDataAPI(ABC):
    """
    Abstract base class defining the standard interface for extracting market data.
    """
    
    @abstractmethod
    def fetch_movers(self, screener_id, **constraints):
        """
        Fetches stock candidates based on screener criteria.
        
        Args:
            screener_id (str): The predefined screener identifier.
            **constraints: Optional filtering parameters such as min_mcap, min_price, etc.
            
        Returns:
            list: A list of candidate dictionaries.
        """
        pass

    @abstractmethod
    def search_by_name(self, query):
        """
        Searches for stock candidates by company name or keyword.
        
        Args:
            query (str): The search query.
            
        Returns:
            list: A list of candidate dictionaries.
        """
        pass

    @abstractmethod
    def fetch_historical_data(self, symbol, period="1y", interval="1d"):
        """
        Fetches historical price data for a specific stock.
        
        Args:
            symbol (str): The stock ticker symbol.
            period (str): The time period to fetch data for. Default is "1y".
            interval (str): The interval of the data. Default is "1d".
            
        Returns:
            pandas.DataFrame: The historical market data.
        """
        pass

    @abstractmethod
    def fetch_company_info(self, symbol):
        """
        Fetches metadata and company information.
        
        Args:
            symbol (str): The stock ticker symbol.
            
        Returns:
            dict: A dictionary containing company information.
        """
        pass
