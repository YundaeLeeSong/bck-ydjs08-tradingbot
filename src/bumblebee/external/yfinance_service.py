"""
Yahoo Finance API Module
========================
Implements the MarketDataAPI using Yahoo Finance.
"""
import os
import json
import requests
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import yfinance as yf
from datetime import datetime
import matplotlib
# Use non-interactive 'Agg' backend to prevent 'Tcl_AsyncDelete' thread safety errors
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List, Optional
from bumblebee.models import StockDataDTO, StockDataTable
from bumblebee.external.matplotlib_service import generate_all_plots
from bumblebee.external.analysis_service import analyze_stock_data

# Suppress specific pandas warnings triggered by yfinance
warnings.filterwarnings("ignore", message=".*Timestamp.utcnow is deprecated.*")
warnings.filterwarnings("ignore", category=FutureWarning)

_DEBUG_LOG_ = "log_yfinance"

class YFinanceService:
    """
    Concrete implementation for fetching and analyzing Yahoo Finance data.
    
    This class is implemented as a Singleton to ensure only one instance
    of the HTTP client/configuration exists throughout the application lifecycle.
    """
    
    _instance = None

    def __new__(cls, debug: bool = False):
        # [Singleton] (1): Allocate the single instance if it doesn't exist.
        if cls._instance is None:
            cls._instance = super(YFinanceService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, debug: bool = False):
        # [Singleton] (2): Initialize configuration once, ignore subsequent __init__ calls.
        if self._initialized:
            return
            
        self.debug = bool(debug)
        if self.debug:
            os.makedirs(_DEBUG_LOG_, exist_ok=True)
            
        self._initialized = True

    def _log_debug(self, operation, request_data, response_data):
        # [Singleton] (3): Invoke instance method
        if not self.debug:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(_DEBUG_LOG_, f"yfinance_{operation}_{timestamp}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== REQUEST ===\n")
            f.write(json.dumps(request_data, indent=2) if isinstance(request_data, dict) else str(request_data))
            f.write("\n\n=== RESPONSE ===\n")
            f.write(str(response_data) + "\n")

    def _get_raw_value(self, data_point, default=0):
        if isinstance(data_point, dict):
            return data_point.get('raw', default)
        return data_point if data_point is not None else default

    def _format_date(self, timestamp):
        if not timestamp or timestamp == 0:
            return "N/A"
        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except:
            return "N/A"

    def fetch_movers(self, screener_id="day_gainers", min_mcap=None, max_mcap=None, min_price=None, min_change=None, max_change=None):
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
                if max_mcap is not None and mcap > max_mcap:
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

    # [Facade] (2): Wraps complex yfinance library behind a simple interface.
    def fetch_historical_data(self, symbol, period="1y", interval="1d"):
        request_data = {"symbol": symbol, "period": period, "interval": interval}
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
            
            # Clean data by removing rows with NaNs to prevent downstream math errors
            if not df.empty:
                df.dropna(inplace=True)
            
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

    def get_winner_tickers(self, **constraints) -> List[str]:
        stocks = self.fetch_movers(screener_id="day_gainers", **constraints)
        return [s['ticker'] for s in stocks]

    def get_loser_tickers(self, **constraints) -> List[str]:
        stocks = self.fetch_movers(screener_id="day_losers", **constraints)
        return [s['ticker'] for s in stocks]

    def get_stock_data(self, symbol: str) -> StockDataDTO:
        df = self.fetch_historical_data(symbol)
        
        # Fallback to basic empty DTO if no data is found
        if df is None or df.empty:
            return StockDataDTO(symbol=symbol, isActive=False)

        # Flatten MultiIndex if yfinance >= 0.2.40 returned one for a single ticker
        df_symbol = self._extract_symbol_df(df, symbol)
        if df_symbol is None or df_symbol.empty:
            return StockDataDTO(symbol=symbol, isActive=False)

        # Build base DTO and run metrics using shared helper
        result = self._create_dto_from_df(symbol, df_symbol)
        if result is None:
            return StockDataDTO(symbol=symbol, isActive=False)
            
        dto, _, _ = result
        
        # Fetch company info specifically for sector/industry/name
        # (This is the only endpoint that requires .info)
        info = self.fetch_company_info(symbol)
        dto.name = info.get('shortName', '') or info.get('longName', '')
        dto.sector = info.get('sector', '')
        dto.industry = info.get('industry', '')
        dto.marketCap = info.get('marketCap', 0)
        
        return dto

    def _extract_symbol_df(self, batch_df: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """
        Extracts a single ticker's DataFrame from a batched MultiIndex DataFrame.
        """
        # 1. Single ticker case (yfinance < 0.2.40 or older pandas behavior)
        if not isinstance(batch_df.columns, pd.MultiIndex):
            return batch_df.copy()
            
        # 2. Validate the symbol exists in the batch
        if symbol not in batch_df.columns.levels[1]:
            return None
            
        # 3. Extract columns belonging to this symbol
        # xs(key, level) allows us to slice out the inner index ('Ticker' level) 
        # from the columns, returning a clean, single-level DataFrame.
        try:
            return batch_df.xs(symbol, axis=1, level=1).copy()
        except KeyError:
            return None

    def _create_dto_from_df(self, symbol: str, df: pd.DataFrame) -> Optional[StockDataDTO]:
        """Calculates basic metrics and returns a StockDataDTO from a DataFrame."""
        if df.empty:
            return None

        # Approximate current price, change, and volume from historical data
        current_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0
        volume = int(df['Volume'].iloc[-1])

        dto = StockDataDTO(
            symbol=symbol,
            price=current_price,
            pct_day_pnl=change_pct,
            volume=volume,
            isAnalyzed=True,
            isActive=True
        )

        df, metrics = analyze_stock_data(df)

        dto.r_squared = metrics.get('r_squared', 0.0)
        dto.slope = metrics.get('slope', 0.0)
        dto.zero_freq = metrics.get('num_zeros', 0)
        dto.pct_mad = metrics.get('mad', 0.0)
        dto.pct_sd = metrics.get('sd', 0.0)

        if metrics.get('priceAvg50') is not None and not metrics['priceAvg50'].empty:
            dto.priceAvg50 = float(metrics['priceAvg50'].iloc[-1])
        if metrics.get('priceAvg200') is not None and not metrics['priceAvg200'].empty:
            dto.priceAvg200 = float(metrics['priceAvg200'].iloc[-1])
        if metrics.get('rsi14') is not None and not metrics['rsi14'].empty:
            dto.rsi14 = float(metrics['rsi14'].iloc[-1])
            
        return dto, df, metrics

    def _save_plots(self, symbol: str, df: pd.DataFrame, metrics: dict, graph_path: str):
        """Generates and saves analysis plots for a given ticker."""
        plots = generate_all_plots(symbol, df, metrics)
        if not plots: return
        
        if 'base_regression' in plots:
            plots['base_regression'].savefig(os.path.join(graph_path, f"{symbol}.png"))
            plt.close(plots['base_regression'])
        if 'pct_ordinary' in plots:
            plots['pct_ordinary'].savefig(os.path.join(graph_path, f"{symbol}_pct_ordinary.png"))
            plt.close(plots['pct_ordinary'])
        if 'pct_derivative' in plots:
            plots['pct_derivative'].savefig(os.path.join(graph_path, f"{symbol}_pct_derivative.png"))
            plt.close(plots['pct_derivative'])

    def get_etf_holdings(self, tickers: List[str], min_mcap: Optional[float] = None, max_mcap: Optional[float] = None) -> List[str]:
        """
        Fetches the unique top holdings tickers for a list of ETFs.
        """
        holdings_set = set()
        for symbol in tickers:
            request_data = {"symbol": symbol}
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.funds_data
                if data is not None and hasattr(data, 'top_holdings'):
                    holdings = data.top_holdings
                    if holdings is not None and not holdings.empty:
                        self._log_debug("get_etf_holdings", request_data, f"Found {len(holdings)} holdings")
                        for h_symbol in holdings.index:
                            if isinstance(h_symbol, str) and h_symbol.isalpha() and h_symbol.isupper() and h_symbol.isascii():
                                holdings_set.add(h_symbol)
                    else:
                        self._log_debug("get_etf_holdings", request_data, "No holdings data returned")
                else:
                    self._log_debug("get_etf_holdings", request_data, "funds_data attribute unavailable")
            except Exception as e:
                self._log_debug("get_etf_holdings_error", request_data, str(e))
                print(f"Error fetching holdings for {symbol}: {e}")
                
        # Always validate the discovered holdings and apply optional market cap filters
        if not holdings_set:
            return []

        # 1. Community standard: Bulk validate all holdings via yf.download to drop invalid tickers quickly
        # This prevents excessive individual API calls and is much more rate-limit friendly.
        holdings_list = list(holdings_set)
        valid_tickers = set()
        
        import sys
        import contextlib
        import io
        import logging
        
        try:
            # Suppress yfinance error output for invalid tickers
            logging.getLogger('yfinance').setLevel(logging.CRITICAL)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                # Batch download 1 day of data to verify existence
                batch_df = yf.download(holdings_list, period="1d", progress=False, auto_adjust=False)
                
            if not batch_df.empty:
                if isinstance(batch_df.columns, pd.MultiIndex):
                    if 'Close' in batch_df:
                        for ticker in holdings_list:
                            if ticker in batch_df['Close'] and not batch_df['Close'][ticker].dropna().empty:
                                valid_tickers.add(ticker)
                else:
                    # Single ticker fallback
                    if 'Close' in batch_df and not batch_df['Close'].dropna().empty:
                        valid_tickers = set(holdings_list)
        except Exception as e:
            self._log_debug("get_etf_holdings_batch_validation_error", {}, str(e))
            valid_tickers = holdings_set  # Fallback
        finally:
            logging.getLogger('yfinance').setLevel(logging.WARNING)

        if not valid_tickers:
            return []

        # If no market cap filtering is needed, return the validated tickers immediately
        if min_mcap is None and max_mcap is None:
            return list(valid_tickers)

        # 2. Filter by market cap using fast_info (community standard to avoid rate limiting on quoteSummary)
        filtered_holdings = []
        from concurrent.futures import ThreadPoolExecutor
        
        def _check_ticker(h_symbol):
            try:
                # fast_info is significantly lighter and faster than .info
                fast_info = yf.Ticker(h_symbol).fast_info
                
                # Check for valid ticker by ensuring basic keys exist
                if not fast_info or 'marketCap' not in fast_info:
                    return None
                    
                mcap = self._get_raw_value(fast_info.get('marketCap', 0))
                if min_mcap is not None and mcap < min_mcap:
                    return None
                if max_mcap is not None and mcap > max_mcap:
                    return None
                return h_symbol
            except Exception as e:
                return None

        # Use ThreadPoolExecutor for the remaining valid tickers
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(_check_ticker, valid_tickers)
            filtered_holdings = [r for r in results if r is not None]
            
        return filtered_holdings

    def get_stocks_table(self, tickers: List[str], graph_path: Optional[str] = None) -> StockDataTable:
        table = StockDataTable()
        if not tickers: return table

        if graph_path: os.makedirs(graph_path, exist_ok=True)
        tickers = list(set(tickers))

        import sys
        import contextlib
        import io
        import logging

        # Perform a single batch download for all tickers to avoid rate limiting
        try:
            logging.getLogger('yfinance').setLevel(logging.CRITICAL)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                batch_df = yf.download(tickers, period="1y", interval="1d", progress=False, auto_adjust=False)
        except Exception as e:
            self._log_debug("batch_fetch_historical_data_error", {"tickers": tickers}, str(e))
            print(f"Failed to batch fetch historical data: {e}")
            return table
        finally:
            logging.getLogger('yfinance').setLevel(logging.WARNING)

        if batch_df is None or batch_df.empty: return table
        
        for symbol in tickers:
            try:
                # Isolate symbol's data and clean
                df_symbol = self._extract_symbol_df(batch_df, symbol)
                if df_symbol is None: continue
                
                df_symbol.dropna(inplace=True)
                if df_symbol.empty: continue

                # Build DTO and run analysis
                result = self._create_dto_from_df(symbol, df_symbol)
                if not result: continue
                dto, df_analyzed, metrics = result
                table.add(dto)

                # Export graphs if requested
                if graph_path:
                    self._save_plots(symbol, df_analyzed, metrics, graph_path)

            except Exception as e:
                self._log_debug("get_stocks_table_symbol_error", {"symbol": symbol}, str(e))
                print(f"Error processing {symbol} from batch: {e}")

        return table
