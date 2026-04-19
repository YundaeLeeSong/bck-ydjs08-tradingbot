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
import matplotlib.pyplot as plt
from typing import List, Optional
from alphavi.models import StockDataDTO, StockDataTable
from alphavi.yfinance.matplotlib_service import generate_all_plots
from alphavi.yfinance.analysis_service import analyze_stock_data

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
        info = self.fetch_company_info(symbol)
        
        price = info.get('currentPrice', info.get('regularMarketPrice', 0.0))
        change_pct = info.get('regularMarketChangePercent', 0.0)
        volume = info.get('volume', info.get('regularMarketVolume', 0))
        mcap = info.get('marketCap', 0)
        company_name = info.get('shortName', '') or info.get('longName', '')
        sector = info.get('sector', '')
        industry = info.get('industry', '')
        
        dto = StockDataDTO(
            symbol=symbol,
            price=price,
            pct_latest_change=change_pct,
            volume=volume,
            marketCap=mcap,
            sector=sector,
            industry=industry,
            name=company_name,
            isAnalyzed=True,
            isActive=True
        )
        
        if df is not None and not df.empty:
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
                
        return dto

    def get_stocks_table(self, tickers: List[str], graph_path: Optional[str] = None) -> StockDataTable:
        table = StockDataTable()
        
        if not tickers:
            return table

        if graph_path:
            os.makedirs(graph_path, exist_ok=True)

        for symbol in tickers:
            dto = self.get_stock_data(symbol)
            table.add(dto)
            
            # Generate and save plots if graph_path is specified
            if graph_path:
                df = self.fetch_historical_data(symbol)
                if df is not None and not df.empty:
                    df, metrics = analyze_stock_data(df)
                    plots = generate_all_plots(symbol, df, metrics)
                    if plots:
                        if 'base_regression' in plots:
                            plots['base_regression'].savefig(os.path.join(graph_path, f"{symbol}.png"))
                            plt.close(plots['base_regression'])
                        if 'pct_ordinary' in plots:
                            plots['pct_ordinary'].savefig(os.path.join(graph_path, f"{symbol}_pct_ordinary.png"))
                            plt.close(plots['pct_ordinary'])
                        if 'pct_derivative' in plots:
                            plots['pct_derivative'].savefig(os.path.join(graph_path, f"{symbol}_pct_derivative.png"))
                            plt.close(plots['pct_derivative'])
            
        return table
