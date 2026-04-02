"""
Yahoo Finance API Module
========================
Implements the MarketDataAPI using Yahoo Finance.
"""
import os
import json
import requests
import warnings
import yfinance as yf
from datetime import datetime
from services.market_data_api import MarketDataAPI

# Suppress specific pandas warnings triggered by yfinance
warnings.filterwarnings("ignore", message=".*Timestamp.utcnow is deprecated.*")
warnings.filterwarnings("ignore", category=FutureWarning)

# [Adapter Pattern]: Integrate external Yahoo APIs into our MarketDataAPI interface.
class YahooFinanceAPI(MarketDataAPI):
    """
    Concrete implementation of MarketDataAPI that integrates with Yahoo Finance APIs.
    """
    
    def __init__(self, debug=False):
        """
        Initializes the YahooFinanceAPI.
        
        Args:
            debug (bool): If True, enables saving of API requests and responses to a debug folder.
        """
        self.debug = debug
        if self.debug:
            os.makedirs("debug", exist_ok=True)

    def _log_debug(self, operation, request_data, response_data):
        """
        Saves API requests and responses to the debug folder if debug mode is enabled.
        
        Args:
            operation (str): The name of the operation being logged.
            request_data (dict or str): The data sent in the request.
            response_data (dict or str): The raw response data received.
            
        Returns:
            None
        """
        if not self.debug:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"debug/YahooFinanceAPI.{operation}_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== REQUEST ===\n")
            f.write(json.dumps(request_data, indent=2) if isinstance(request_data, dict) else str(request_data))
            f.write("\n\n=== RESPONSE ===\n")
            f.write(str(response_data) + "\n")

    def _get_raw_value(self, data_point, default=0):
        """
        Extracts raw numeric values from complex JSON objects.
        
        Args:
            data_point (dict or any): The data point which could be a dictionary with a 'raw' key.
            default (any): The default value to return if extraction fails.
            
        Returns:
            any: The raw extracted value or the default.
        """
        if isinstance(data_point, dict):
            return data_point.get('raw', default)
        return data_point if data_point is not None else default

    def _format_date(self, timestamp):
        """
        Converts Unix timestamps to YYYY-MM-DD or 'N/A'.
        
        Args:
            timestamp (int or None): The Unix timestamp to convert.
            
        Returns:
            str: The formatted date string or 'N/A'.
        """
        if not timestamp or timestamp == 0:
            return "N/A"
        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except:
            return "N/A"

    def fetch_movers(self, screener_id="day_gainers", min_mcap=None, min_price=None, min_change=None, max_change=None):
        """
        Queries Yahoo for candidates satisfying the specific trading conditions.
        
        Args:
            screener_id (str): Yahoo predefined screener ID (e.g., 'day_gainers', 'day_losers').
            min_mcap (float): Optional minimum market capitalization.
            min_price (float): Optional minimum stock price.
            min_change (float): Optional minimum percentage change.
            max_change (float): Optional maximum percentage change.
            
        Returns:
            list: A sorted list of dictionaries containing stock information.
        """
        url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=true&scrIds={screener_id}&count=100"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        request_data = {"url": url, "headers": headers, "screener_id": screener_id}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            raw_json = response.json()
            
            self._log_debug("fetch_movers", request_data, json.dumps(raw_json, indent=2))
            
            results = raw_json.get('finance', {}).get('result', [{}])[0].get('quotes', [])
            
            candidates = []
            for stock in results:
                mcap = self._get_raw_value(stock.get('marketCap'))
                change = self._get_raw_value(stock.get('regularMarketChangePercent'))
                vol = self._get_raw_value(stock.get('regularMarketVolume'))
                ex_div = self._format_date(self._get_raw_value(stock.get('exDividendDate'))).strip()
                price = self._get_raw_value(stock.get('regularMarketPrice'))
                
                # Base logic: Must not have ex-dividend date set right now
                if ex_div != "N/A":
                    continue
                    
                # Filter logic: Apply only the constraints that were provided
                if min_mcap is not None and mcap < min_mcap:
                    continue
                if min_price is not None and price < min_price:
                    continue
                if min_change is not None and change < min_change:
                    continue
                if max_change is not None and change > max_change:
                    continue

                candidates.append({
                    'ticker': stock.get('symbol'),
                    'price': price,
                    'change': change,
                    'mcap': mcap,
                    'volume': vol,
                    'name': stock.get('shortName', stock.get('longName', ''))
                })
                
            return sorted(candidates, key=lambda x: abs(x['change']), reverse=True)
        except Exception as e:
            self._log_debug("fetch_movers_error", request_data, str(e))
            print(f"Error fetching data: {e}")
            return []

    def search_by_name(self, query):
        """
        Queries Yahoo search API to find tickers related to a company name.
        
        Args:
            query (str): The search query (e.g., 'yieldmax').
            
        Returns:
            list: A list of dictionaries containing basic stock information.
        """
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=100"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        request_data = {"url": url, "headers": headers, "query": query}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            raw_json = response.json()
            
            self._log_debug("search_by_name", request_data, json.dumps(raw_json, indent=2))
            
            results = raw_json.get('quotes', [])
            
            candidates = []
            for stock in results:
                long_name = stock.get('longname', '')
                short_name = stock.get('shortname', '')
                
                # Verify the query is actually in the name
                name_to_check = (long_name + " " + short_name).lower()
                if query.lower() not in name_to_check:
                    continue
                    
                candidates.append({
                    'ticker': stock.get('symbol'),
                    'price': 0.0, # We'll need to fetch price later
                    'change': 0.0,
                    'mcap': 0,
                    'volume': 0,
                    'name': long_name or short_name
                })
                
            return candidates
        except Exception as e:
            self._log_debug("search_by_name_error", request_data, str(e))
            print(f"Error searching by name: {e}")
            return []

    # [Facade Pattern]: Wraps complex yfinance library behind a simple interface.
    def fetch_historical_data(self, symbol, period="1y", interval="1d"):
        """
        Fetches historical stock data using yfinance.
        
        Args:
            symbol (str): The stock ticker symbol.
            period (str): The time period to fetch data for. Default is "1y".
            interval (str): The interval of the data. Default is "1d".
            
        Returns:
            pandas.DataFrame: The historical data, or None if the fetch fails.
        """
        request_data = {"symbol": symbol, "period": period, "interval": interval}
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
            
            # Log first few rows and total length
            if not df.empty:
                response_str = df.head().to_string() + f"\n... [{len(df)} rows total]"
            else:
                response_str = "Empty DataFrame"
            self._log_debug("fetch_historical_data", request_data, response_str)
            
            return df
        except Exception as e:
            self._log_debug("fetch_historical_data_error", request_data, str(e))
            print(f"Failed to fetch data for {symbol}: {e}")
            return None

    def fetch_company_info(self, symbol):
        """
        Fetches basic company information using yfinance.
        
        Args:
            symbol (str): The stock ticker symbol.
            
        Returns:
            dict: A dictionary containing company information, or an empty dict if the fetch fails.
        """
        request_data = {"symbol": symbol}
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            self._log_debug("fetch_company_info", request_data, json.dumps(info, indent=2))
            return info
        except Exception as e:
            self._log_debug("fetch_company_info_error", request_data, str(e))
            print(f"Failed to fetch info for {symbol}: {e}")
            return {}
