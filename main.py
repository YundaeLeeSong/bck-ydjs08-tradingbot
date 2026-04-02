"""
Stock Analysis & Regression Tool v3.0
------------------------------------
1. Logic: Generates all historical regression graphs (1Y) first.
2. Filters: Market Cap >= $1B, Gain >= 10%, No Ex-Div Date.
3. Display: Shows a summary table including Volume at the very end.
"""

import os
import requests
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from datetime import datetime

# --- Configuration ---
DIR_NAME = "./shorting_data"
MIN_MCAP = 1_000_000_000
MIN_GAIN = 10.0

def get_raw_value(data_point, default=0):
    """Extracts raw numeric values from Yahoo's complex JSON objects."""
    if isinstance(data_point, dict):
        return data_point.get('raw', default)
    return data_point if data_point is not None else default

def format_date(timestamp):
    """Converts Unix timestamps to YYYY-MM-DD or 'N/A'."""
    if not timestamp or timestamp == 0:
        return "N/A"
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except:
        return "N/A"

def get_filtered_movers():
    """Queries Yahoo for candidates satisfying the specific trading conditions."""
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=true&scrIds=day_gainers&count=100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        results = response.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
        
        candidates = []
        for stock in results:
            mcap = get_raw_value(stock.get('marketCap'))
            gain = get_raw_value(stock.get('regularMarketChangePercent'))
            vol = get_raw_value(stock.get('regularMarketVolume'))
            ex_div = format_date(get_raw_value(stock.get('exDividendDate'))).strip()
            
            # Filter logic: $1B+ Cap, 10%+ Gain, No Ex-Div Date
            if mcap >= MIN_MCAP and gain >= MIN_GAIN and ex_div == "N/A":
                candidates.append({
                    'ticker': stock.get('symbol'),
                    'price': get_raw_value(stock.get('regularMarketPrice')),
                    'change': gain,
                    'mcap': mcap,
                    'volume': vol
                })
        # Sort by gain descending
        return sorted(candidates, key=lambda x: x['change'], reverse=True)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def generate_regression_plots(stocks):
    """
    Fetches 1Y data and saves linear regression plots to ./shorting_data.
    Displays error metrics and regression lines.
    """
    if not os.path.exists(DIR_NAME):
        os.makedirs(DIR_NAME)
        print(f"Created/Verified directory: {DIR_NAME}")

    for s in stocks:
        symbol = s['ticker']
        print(f"Graphing {symbol} (1Y Data)...")
        try:
            # period="1y" as requested
            df = yf.download(symbol, period="1y", interval="1d", progress=False)
            if df.empty:
                continue

            # Linear regression prep
            y = df['Close'].values.flatten()
            x = np.arange(len(y))

            # Statistics calculation
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            line = slope * x + intercept
            r_squared = r_value ** 2

            # Visual Generation
            plt.figure(figsize=(10, 5))
            plt.plot(df.index, y, label='Daily Close', color='#1f77b4', alpha=0.6)
            plt.plot(df.index, line, label='1Y Trendline', color='red', linestyle='--')
            
            plt.title(f"{symbol} 1Y Regression | R-Squared: {r_squared:.4f}")
            plt.ylabel("Price (USD)")
            plt.grid(True, linestyle=':', alpha=0.6)
            
            # Error and Stats overlay
            stats_box = (f"Slope: {slope:.4f}\n"
                         f"Std Error: {std_err:.4f}\n"
                         f"R^2: {r_squared:.4f}")
            plt.gca().text(0.02, 0.95, stats_box, transform=plt.gca().transAxes,
                           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.savefig(os.path.join(DIR_NAME, f"{symbol}.png"))
            plt.close()

        except Exception as e:
            print(f"Failed to process {symbol}: {e}")

def main():
    print("Initiating Market Scan...")
    stocks = get_filtered_movers()
    
    if not stocks:
        print("No stocks matched the criteria today.")
        return

    # Phase 1: Process Graphs First
    print(f"Found {len(stocks)} candidates. Starting analysis...")
    generate_regression_plots(stocks)
    print("Analysis complete. All graphs saved to ./shorting_data\n")

    # Phase 2: Display Summary Table
    header = f"{'Ticker':<10} | {'Price':<10} | {'% Gain':<10} | {'Volume':<12} | {'Market Cap':<12}"
    print(header)
    print("-" * len(header))
    
    for s in stocks:
        # Convert values for readability
        mcap_billions = s['mcap'] / 1_000_000_000
        vol_millions = s['volume'] / 1_000_000
        
        print(f"{s['ticker']:<10} | "
              f"{s['price']:<10.2f} | "
              f"{s['change']:>8.2f}% | "
              f"{vol_millions:>10.2f}M | "
              f"{mcap_billions:>10.2f}B")

if __name__ == "__main__":
    main()