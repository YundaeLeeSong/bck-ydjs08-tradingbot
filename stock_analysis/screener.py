"""
Screener Module
===============
Responsible for querying financial APIs to find stock candidates based on
predefined criteria.
"""
import requests
from datetime import datetime

def _get_raw_value(data_point, default=0):
    """
    Extracts raw numeric values from complex JSON objects.
    """
    if isinstance(data_point, dict):
        return data_point.get('raw', default)
    return data_point if data_point is not None else default

def _format_date(timestamp):
    """
    Converts Unix timestamps to YYYY-MM-DD or 'N/A'.
    """
    if not timestamp or timestamp == 0:
        return "N/A"
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except:
        return "N/A"

def get_filtered_movers(screener_id="day_gainers", min_mcap=None, min_price=None, min_change=None, max_change=None):
    """
    Queries Yahoo for candidates satisfying the specific trading conditions.
    
    Args:
        screener_id (str): Yahoo predefined screener ID (e.g., 'day_gainers', 'day_losers').
        min_mcap (float): Minimum market capitalization.
        min_price (float): Minimum stock price.
        min_change (float): Minimum percentage change (lower bound).
        max_change (float): Maximum percentage change (upper bound).
        
    Returns:
        list: A sorted list of dictionaries containing stock information.
    """
    url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=true&scrIds={screener_id}&count=100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        results = response.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
        
        candidates = []
        for stock in results:
            mcap = _get_raw_value(stock.get('marketCap'))
            change = _get_raw_value(stock.get('regularMarketChangePercent'))
            vol = _get_raw_value(stock.get('regularMarketVolume'))
            ex_div = _format_date(_get_raw_value(stock.get('exDividendDate'))).strip()
            price = _get_raw_value(stock.get('regularMarketPrice'))
            
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
                'volume': vol
            })
            
        # Sort by absolute change descending for biggest movers
        return sorted(candidates, key=lambda x: abs(x['change']), reverse=True)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []
