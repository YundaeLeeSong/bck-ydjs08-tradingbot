# alpaca_tradebot/core.py

########## broker API reference: https://github.com/alpacahq/alpaca-py
########## price reference: https://stockanalysis.com/stocks/orcl/forecast/"
import sys
import time
import os
import json

import csv
import requests
import time
from dotenv import load_dotenv
import pandas as pd

# Fix pandas Timestamp.utcnow deprecation (used by yfinance internals).
# Patch to the recommended API so no deprecated code path runs.
if hasattr(pd.Timestamp, "utcnow"):
    def _timestamp_utcnow():
        return pd.Timestamp.now(tz="UTC")
    pd.Timestamp.utcnow = staticmethod(_timestamp_utcnow)

from pathlib import Path
import pytz
from typing import List
from datetime import datetime, timedelta, time as dtime

from .orders import cancel_order, load_orders, fetch_orders,save_orders_to_csv, cancel_all_orders_in, cancel_order_by_asset
# from .fsm import run as fsm_on
from .research import do_research
from .libra import get_asset_state, get_equiv_asset_etf, MK_INDEX_ASSETS, is_bear_etf

from .option import get_current_week_of_month, get_div_asset_list, HIGH_DIVIDEND_ASSETS, is_last_div, is_not_div_sell, EXPIRED_DIVIDEND_ASSETS
from .tax_report import generate_tax_report


import math
from mathx import *
from pvm import get_resource

import sys
sys.stdout.reconfigure(encoding='utf-8')











# ─── 0) Load .env ─────────────────────────────────────────────────────────────
load_dotenv(get_resource(".env"))

PURCHASING_POWER = int(os.getenv("PURCHASING_POWER", 240))
BASE_URL   = os.getenv("APCA_API_BASE_URL")
API_KEY    = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
TRADING_USERNAME = os.getenv("TRADING_USERNAME", "null")

if not (API_KEY and API_SECRET):
    BASE_URL="https://paper-api.alpaca.markets"
    API_KEY="PKD7M8VMC1D6YOQ6CW57"
    API_SECRET="4Euz3jubAEwIvboqeWcJRkbuROGqCFNJ7OzNPLUe"

HEADERS = {
    "APCA-API-KEY-ID":     API_KEY,
    "APCA-API-SECRET-KEY": API_SECRET,
    "Content-Type":        "application/json"
}

SIDE_LIST       = ["buy", "sell"]
ORDER_TYPE_LIST = ["market", "limit", "stop", "stop_limit"]
TIF_LIST        = ["day", "gtc", "opg", "cls", "ioc", "fok"]





# ─── 1) CONSTANTS ──────────────────────────────────────────────────────────
MIN_PCT_AMP = 7.00
# Partition the real number line into intervals based on TRIG_DISTROS
# and assign a label or action for each interval.
DISTRO_BUFFER = 1.25
TRIG_DISTROS = [
    1.000,
    0.824,
    0.594,
    0.360,
    0.000,
    -0.360 * DISTRO_BUFFER,
    -0.594 * DISTRO_BUFFER,
    -0.824 * DISTRO_BUFFER,
    -1.000 * DISTRO_BUFFER,
]
LIMIT_OFFSET_RATE=1.275 # 3.00% -> 3.825% (+27.5%, being cheap when buying)
STOPP_OFFSET_RATE=0.875 # 3.00% -> 2.475% (-12.5%, more chance to raise)







from typing import Callable

def get_strategy(scale: float = 0.195, base: float = 0.0483) -> Callable[[float], float]:
    """
    Implements the Functional Factory Pattern (Closure).
    
    Design Pattern:
    This function acts as a factory that captures the configuration state 
    (scale, base) in a local scope and returns a specialized function 
    (get_rate) that only requires the variable input (plpc).

    Args:
        scale (float): The multiplier constant (default: 0.195).
        base (float): The exponential base (default: 0.0483).

    Returns:
        Callable[[float], float]: A configured function to calculate rates.
    """
    def get_rate(plpc: float) -> float:
        """
        Calculates the rebalance rate for a given plpc.
        
        Args:
            plpc (float): The profit/loss percentage (e.g., -0.20).
            
        Returns:
            float: The calculated discount rate applied rate.
            
        Raises:
            ValueError: If |plpc| is greater than 1.0.
        """
        if abs(plpc) > 1.0: raise ValueError(f"profit/loss percentage {plpc} is out of bounds [-1, 1]")
        return 1 - scale * (base ** abs(plpc))
    return get_rate

GET_RATE = get_strategy()

# # ------------------------------------------------------------------
# # Usage
# # ------------------------------------------------------------------
# if __name__ == "__main__":
#     current_plpc = -0.12
#     print(f"profit/loss percentage: {current_plpc}")
#     print(f"Rebalance Rate for Current Price: {GET_RATE(current_plpc) * 100:.2f}%")
        










def load_nonfract_assets_info() -> None:
    fetch_and_save("assets", Path("alpaca_data2")/Path("assets.json"))
    # read json file from "alpaca_data2/assets.json"
    with open('alpaca_data2/assets.json', 'r') as file:
        assets = json.load(file)
        asset_list = []
        for asset in assets:
            # if symbol has non-english letters or contains '/', continue
            if (not asset['symbol'].isascii() or '/' in asset['symbol'] or '.' in asset['symbol']): continue
            # if not tradable, continue
            if (not asset['tradable']): continue
            # creat an array of assets information.
            row = [asset['symbol'], asset['tradable'], asset['shortable'], asset['fractionable']]
            asset_list.append(row)
    # write a csv file with asset_list
    with open('alpaca_data2/assets.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # set the header info
        writer.writerow(["symbol", "tradable", "shortable", "fractionable"])  # Writes the header row
        # fill out rows
        writer.writerows(asset_list)



def get_nonfract_assets(csv_path: Path) -> List[str]:
    """
    Read a CSV of assets (with columns 'symbol' and 'fractionable') and
    return a list of symbols that are not fractionable.
    
    Args:
      csv_path: Path to the CSV file (expects a header with 'symbol' and 'fractionable').
    
    Returns:
      A list of symbols (strings) for which fractionable == False.
    """
    nonfract_symbols: List[str] = []
    
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # CSV stores booleans as text, so normalize and check
            frac = row["fractionable"].strip().lower()
            if frac in ("false", "0", ""):
                nonfract_symbols.append(row["symbol"])
    
    return nonfract_symbols


NONFRACT_ASSETS=get_nonfract_assets(Path("alpaca_data2/assets.csv"))






def is_extended_hours(now=None):
    """
    Returns True if the current time (US/Eastern) is in extended hours for the US stock market.
    Extended hours are:
      - Pre-market: 04:00:01 to 09:29:59
      - Post-market: 16:00:01 to 19:59:59
    Args:
        now (datetime, optional): The time to check. If None, uses current time.
    Returns:
        bool: True if in extended hours, False otherwise.
    """
    eastern = pytz.timezone('US/Eastern')
    if now is None: now = datetime.now(eastern)
    else:
        if now.tzinfo is None: now = eastern.localize(now)
        else:  now = now.astimezone(eastern)
    t = now.time()
    pre_start = dtime(4, 0, 1)      # 4:00 AM ET
    pre_end = dtime(9, 29, 59)      # 9:30 AM ET
    post_start = dtime(16, 0, 1)    # 4:00 PM ET
    post_end = dtime(19, 59, 59)    # 8:00 PM ET 
    if pre_start <= t <= pre_end: return True
    if post_start <= t <= post_end: return True
    return False






















# ─── helper to GET & print JSON ────────────────────────────────────────────────
def get_and_print(endpoint):
    """
    GET /v2/{endpoint}, raise on error, and pretty-print the JSON result.
    """
    url = f"{BASE_URL}/v2/{endpoint}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    print(f"\n=== {endpoint.upper()} ===")
    print(data)


# ─── helper to GET & print JSON ────────────────────────────────────────────────
def get_data():
    """
    GET /v2/{endpoint}, raise on error, and pretty-print the JSON result.
    """
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    return data


def get_price(symbol: str) -> float:
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        if not data.empty: return round(float(data["Close"].iloc[-1]), 2)  # last available close
        else: raise ValueError(f"No data available for symbol: {symbol}")
    except Exception as e:
        log_path = "alpaca_data2/log.txt"
        with open(log_path, "a") as log_file:
            log_file.write(
                f"[{datetime.now()}] Failed to get price for {symbol}: {e}\n"
            )
        return None  # or float('nan')




def place_order(
    symbol: str,
    side: str,
    order_type: str = "limit",
    tif: str = "day",
    limit_price: float = None,
    qty: float = None,
    stop_price: float = None,
    isExtHour: bool = False,
) -> dict:
    """
    Place an order. All arguments must be provided and valid, or an error is raised.
    Optionally enable extended hours trading if isExtHour is True.

    Args:
        symbol (str): Ticker symbol.
        side (str): "buy" or "sell".
        order_type (str): Order type ("market", "limit", etc).
        tif (str): Time in force.
        limit_price (float): Limit price.
        qty (float): Quantity of shares.
        stop_price (float): Stop price.
        isExtHour (bool): Whether to enable extended hours trading (default: False)

    Returns:
        dict: API response.
    """
    # Validate required fields before proceeding
    if not symbol or not isinstance(symbol, str): raise ValueError("symbol must be provided as a string")
    if side not in SIDE_LIST: raise ValueError(f"side must be one of {SIDE_LIST}")
    if order_type not in ORDER_TYPE_LIST: raise ValueError(f"order_type must be one of {ORDER_TYPE_LIST}")
    if tif not in TIF_LIST: raise ValueError(f"tif must be one of {TIF_LIST}")
    if order_type in ("limit", "stop_limit") and limit_price is None: raise ValueError("limit_price required for limit or stop_limit orders")
    if order_type in ("stop", "stop_limit") and stop_price is None: raise ValueError("stop_price required for stop or stop_limit orders")
    if qty is None: raise ValueError("qty of shares must be provided")

    payload = {
        "symbol":        symbol,
        "side":          side,
        "type":          order_type,
        "time_in_force": tif,
        "qty":           qty,
        # limit_price: float = None,
        # stop_price: float = None,
    } 
    if order_type in ("limit", "stop_limit"): payload["limit_price"] = float(limit_price)
    if order_type in ("stop", "stop_limit"): payload["stop_price"] = float(stop_price)
    if isExtHour:
        # --- Extended Hours Logic ---
        # All extended hours requirements are handled here:
        # 1. extended hours order must be DAY limit orders
        # 2. Set extended_hours=True in the API payload
        if order_type in ("market", "stop", "stop_limit"): raise ValueError('extended hours orders must be "limit" orders') 
        if tif != "day": raise ValueError('extended hours orders must have a time in force of "DAY"')
        payload["extended_hours"] = True
    # Submit
    url = f"{BASE_URL}/v2/orders"
    return post(url, HEADERS, payload)



def post(url, headers, payload):
    """
    Sends a POST request and returns the JSON response.

    Args:
        url (str): The endpoint URL.
        headers (dict): HTTP headers.
        payload (dict): The request body.

    Returns:
        dict: The JSON response.
    """
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()



def post_with_debug(url, headers, payload):
    print("→ Request URL:   ", url)
    print("→ Request headers:", headers)
    print("→ Request body:  ", json.dumps(payload, indent=2))
    resp = requests.post(url, json=payload, headers=headers)

    # print("Parsed JSON:", json.dumps(resp.json(), indent=2)) # debugging line

    # try to print any returned JSON error:
    try:
        print("← Response code: ", resp.status_code)
        print("← Response body: ", json.dumps(resp.json(), indent=2))
    except ValueError:
        print("← Response body (raw):", resp.text)
    resp.raise_for_status()
    return resp.json()



HOLD_ASSETS = [
    "SEV",
]


def long_limit_buy(asset: str, target_qty: float, target_price: float, isExtHour: bool = False):
    """
    Place a limit buy order with a longer time-in-force.
    Optionally enable extended hours trading (pre/post market) if isExtHour is True.
    
    Args:
        asset (str): The asset symbol to buy
        target_qty (float): Quantity to buy
        target_price (float): Limit price to buy at
        isExtHour (bool): Whether to enable extended hours trading (default: False)
    """
    target_qty = max(int(target_qty), 1) if asset in NONFRACT_ASSETS else round(target_qty, 2)
    target_price = round(target_price, 2)
    try:
        # [POST/buy] Limit order with a longer time-in-force (long-lived, must target price)
        order = place_order(
            symbol=asset,side="buy",
            order_type="limit",tif="day",
            limit_price=target_price,qty=target_qty,
            isExtHour=isExtHour
        )
        time.sleep(0.5) # Delay for 0.5 sec (half a second)
    except Exception as e:
        log_path = "alpaca_data2/log.txt"
        if hasattr(e, 'response') and e.response is not None: resp_json = e.response.json()
        print(json.dumps(resp_json, indent=2))
        with open(log_path, "a") as log_file:
            log_file.write(
                f"[{datetime.now()}] Failed to place buy order for {asset}: "
                f"qty={target_qty}, price={target_price}, error={e}, message={resp_json.get('message', '')}\n"
            )

def long_limit_sell(asset: str, target_qty: float, target_price: float, isExtHour: bool = False):
    """
    Place a limit sell order with a longer time-in-force.
    Optionally enable extended hours trading (pre/post market) if isExtHour is True.
    
    Args:
        asset (str): The asset symbol to sell
        target_qty (float): Quantity to sell
        target_price (float): Limit price to sell at
        isExtHour (bool): Whether to enable extended hours trading (default: False)
    """
    if (asset in HOLD_ASSETS):
        print(f"⚠️  HOLD_ASSETS: Skipping sell order for {asset}")
        return
    target_qty = max(int(target_qty), 1) if asset in NONFRACT_ASSETS else round(target_qty, 2)
    target_price = round(target_price, 2)
    try:
        # [POST/sell] Limit order with a longer time-in-force (long-lived, must target price)
        order = place_order(
            symbol=asset,side="sell",
            order_type="limit",tif="day",
            limit_price=target_price,qty=target_qty,
            isExtHour=isExtHour
        )
        time.sleep(0.5) # Delay for 0.5 sec (half a second)
    except Exception as e:
        log_path = "alpaca_data2/log.txt"
        if hasattr(e, 'response') and e.response is not None: resp_json = e.response.json()
        print(json.dumps(resp_json, indent=2))
        with open(log_path, "a") as log_file:
            log_file.write(
                f"[{datetime.now()}] Failed to place sell order for {asset}: "
                f"qty={target_qty}, price={target_price}, error={e}, message={resp_json.get('message', '')}\n"
            )

def long_stop_sell(asset: str, target_qty: float, target_price: float): 
    """
    Place a stop sell order with a longer time-in-force.
    
    Args:
        asset (str): The asset symbol to sell
        target_qty (float): Quantity to sell
        target_price (float): Stop price to trigger the sell
    """
    if (asset in HOLD_ASSETS):
        print(f"⚠️  HOLD_ASSETS: Skipping sell order for {asset}")
        return
    target_qty = max(int(target_qty), 1) if asset in NONFRACT_ASSETS else round(target_qty, 2)
    target_price = round(target_price, 2)
    try:
        # [POST/sell] Stop order with a longer time-in-force (long-lived, triggers at target price)
        order = place_order(
            symbol=asset,side="sell",
            order_type="stop",tif="day",
            stop_price=target_price,qty=target_qty
        )
        time.sleep(0.5) # Delay for 0.5 sec (half a second)
    except Exception as e:
        log_path = "alpaca_data2/log.txt"
        if hasattr(e, 'response') and e.response is not None: resp_json = e.response.json()
        print(json.dumps(resp_json, indent=2))
        with open(log_path, "a") as log_file:
            log_file.write(
                f"[{datetime.now()}] Failed to place stop sell order for {asset}: "
                f"qty={target_qty}, price={target_price}, error={e}, message={resp_json.get("message", "")}\n"
            )

def long_market_buy(asset: str, target_qty: float): 
    """
    Place a market buy order for immediate execution at current market price.
    
    Args:
        asset (str): The asset symbol to buy
        target_qty (float): Quantity to buy
    """
    target_qty = max(int(target_qty), 1) if asset in NONFRACT_ASSETS else round(target_qty, 2)
    try:
        # [POST/buy] Market order for immediate execution
        order = place_order(
            symbol=asset,side="buy",
            order_type="market",tif="day",
            qty=target_qty
        )
        time.sleep(0.5) # Delay for 0.5 sec (half a second)
    except Exception as e:
        log_path = "alpaca_data2/log.txt"
        if hasattr(e, 'response') and e.response is not None: resp_json = e.response.json()
        print(json.dumps(resp_json, indent=2))
        with open(log_path, "a") as log_file:
            log_file.write(
                f"[{datetime.now()}] Failed to place market buy order for {asset}: "
                f"qty={target_qty}, error={e}, message={resp_json.get("message", "")}\n"
            )

def short_sell(
    asset: str, 
    tgt_qty: float, 
    curr_price: float, 
    ):
    """
    Place a manual short (sell) order with bracket (take profit and stop loss).

    Args:
        asset (str): The asset symbol.
        tgt_qty (float): Quantity to short.
        curr_price (float): Current market price.
    """

    tgt_price = curr_price * (1 + 0.07)                 # Target price is 7% above current price
    tgt_qty = int(tgt_qty)
    if tgt_qty < 1: tgt_qty = 1

    payload = {
        "symbol": asset,
        "qty": tgt_qty,
        "side": "sell",     # short
        "type": "limit",     # Not market — you control the price
        "limit_price": round(tgt_price, 2),  # Only sell if price hits this (7% above current)
        "time_in_force": "day",
        # "order_class": "bracket",     # bracket (take profit and stop loss)
        "order_class": "oto",           # one-triggers-other
        # "stop_loss": { "stop_price": round(tgt_price * (1 + 0.03), 2) },    # Stop loss at 3% above current price
        "take_profit": { "limit_price": round(tgt_price * (1 - 0.03), 2) }, # Take profit at 3% below target price
        # "extended_hours": True
    }

    url = f"{BASE_URL}/v2/orders"
    try:
        obj= post(url, HEADERS, payload)
        print(f"\tshort_sell of {asset} x {tgt_qty} @{round(tgt_price, 2)}")
        # load_orders("alpaca_data2/orders.json")
        return obj
    except Exception as e:
        log_path = "alpaca_data2/log.txt"
        # print("Parsed JSON:", json.dumps(e.response.json(), indent=2)) # debugging line
        if hasattr(e, 'response') and e.response is not None: resp_json = e.response.json()
        print(json.dumps(resp_json, indent=2))
        with open(log_path, "a") as log_file:
            log_file.write(
                f"[{datetime.now()}] Failed to place sell order for {asset}: "
                f"qty={tgt_qty}, price={tgt_price}, error={e}, message={resp_json.get("message", "")}\n"
            )


















































##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################   report
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################


def load_trades_activity(
        file_path: Path = None, 
        date_string: str = None, 
        append: bool = False, 
        cumulative_file_path: Path = None):
    """
    Fetch and save FILL (trade) activities to Excel file using API parameters.
    Gets the latest 100 FILL transactions for a specific date or today.
    
    Args:
        file_path (Path, optional): Custom file path to save the Excel file. If None, uses default path.
        date_string (str, optional): Date in YYYY-MM-DD format. If None, uses today's date.
        append (bool): If True, append to existing file. If False, overwrite existing file.
        cumulative_file_path (Path, optional): Path to cumulative file. If provided, data will be appended to this file.

    Usage:
        ### [LOAD] Process multiple days (June 17-20)
        dates_to_process = ["2025-06-17", "2025-06-18", "2025-06-19", "2025-06-20"]
        for i, date_str in enumerate(dates_to_process):
            if i == 0: load_trades_activity(file_path, date_str, append=False) # First date: create new file
            else: load_trades_activity(file_path, date_str, append=True) # Subsequent dates: append to existing file
        
        ### [LOAD] With cumulative file
        load_trades_activity(
            file_path=Path(f"report/{today}-trades.xlsx"),
            cumulative_file_path=Path("report/transaction-Jaehoon.xlsx")
        )
    """
    try:
        # Determine the date to use
        if date_string is None:
            # Use today's date
            target_date = datetime.now().strftime('%Y-%m-%d')
        else:
            # Use the provided date string
            target_date = date_string
        
        # Fetch FILL activities directly from API with parameters
        url = f"{BASE_URL}/v2/account/activities"
        params = {
            "activity_types": "FILL",
            "limit": 100,
            "date": target_date
        }
        
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        activities_data = resp.json()
        
        if not activities_data:
            print(f"No FILL activities found for date: {target_date}")
            return
        
        # Process each FILL activity
        processed_records = []
        for activity in activities_data:
            # Extract data from activity
            side = activity.get('side', '').upper()
            qty = float(activity.get('qty', 0))
            symbol = activity.get('symbol', '')
            price = float(activity.get('price', 0))
            transaction_time = activity.get('transaction_time', '')
            
            # Calculate total value
            total_value = qty * price
            
            # Format the transaction time
            try:
                dt = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
                # Convert UTC to local timezone
                local_dt = dt.astimezone()
                formatted_time = local_dt.strftime('%b %d, %Y, %I:%M:%S %p')
            except:
                formatted_time = transaction_time
            
            # Create description
            description = f"{side} {qty} {symbol}"
            
            # Add to processed records
            processed_records.append({
                'Description': description,
                'Type': 'FILL',
                'Qty': float(qty),
                'Amount': abs(float(total_value)) if side.startswith('SELL') else -abs(float(total_value)),
                'Date': formatted_time
            })
        
        # Determine file path
        if file_path is None:
            # Use default path
            current_date = datetime.now().strftime('%Y%m%d')
            excel_filename = Path(f"./{current_date}-activities_trades.xlsx")
        else:
            # Use custom path
            excel_filename = file_path
        
        # Ensure directory exists
        excel_filename.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle cumulative file if provided
        if cumulative_file_path is not None:
            # Ensure cumulative file directory exists
            cumulative_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create DataFrame for new data with consistent column order
            new_df = pd.DataFrame(processed_records)
            
            # Define the expected column order
            expected_columns = ['Description', 'Type', 'Qty', 'Amount', 'Date']
            
            # Ensure new_df has the correct column order
            new_df = new_df[expected_columns]
            
            # Append to cumulative file
            if cumulative_file_path.exists():
                # Read existing cumulative data and append new data
                existing_cumulative_df = pd.read_excel(cumulative_file_path)
                
                # Ensure existing data has the correct column order
                if set(existing_cumulative_df.columns) == set(expected_columns):
                    existing_cumulative_df = existing_cumulative_df[expected_columns]
                else:
                    # If column structure is different, reorder to match expected columns
                    print(f"\t⚠️ Warning: Existing cumulative file has different column structure. Reordering columns.")
                    # Try to map existing columns to expected columns
                    column_mapping = {}
                    for col in expected_columns:
                        if col in existing_cumulative_df.columns:
                            column_mapping[col] = col
                        else:
                            # Try to find similar columns
                            for existing_col in existing_cumulative_df.columns:
                                if col.lower() in existing_col.lower() or existing_col.lower() in col.lower():
                                    column_mapping[col] = existing_col
                                    break
                    
                    # Reorder existing data
                    reordered_columns = [column_mapping.get(col, col) for col in expected_columns]
                    existing_cumulative_df = existing_cumulative_df[reordered_columns]
                    existing_cumulative_df.columns = expected_columns
                
                # Combine data with consistent column order
                combined_cumulative_df = pd.concat([existing_cumulative_df, new_df], ignore_index=True)
                combined_cumulative_df.to_excel(cumulative_file_path, index=False)
                print(f"\t✔ Appended {len(processed_records)} FILL activities for {target_date} to cumulative file {cumulative_file_path}")
            else:
                # Create new cumulative file with correct column order
                new_df.to_excel(cumulative_file_path, index=False)
                print(f"\t✔ Created cumulative file with {len(processed_records)} FILL activities for {target_date} at {cumulative_file_path}")
        
        # Handle regular file writing (append or overwrite)
        if append and excel_filename.exists():
            # Read existing data and append new data
            existing_df = pd.read_excel(excel_filename)
            new_df = pd.DataFrame(processed_records)
            
            # Ensure consistent column order for regular file too
            expected_columns = ['Description', 'Type', 'Qty', 'Amount', 'Date']
            new_df = new_df[expected_columns]
            
            if set(existing_df.columns) == set(expected_columns):
                existing_df = existing_df[expected_columns]
            else:
                # Reorder existing data to match expected columns
                existing_df = existing_df[expected_columns]
            
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_excel(excel_filename, index=False)
            print(f"\t✔ Appended {len(processed_records)} FILL activities for {target_date} to {excel_filename}")
        else:
            # Create new file or overwrite existing
            df = pd.DataFrame(processed_records)
            # Ensure consistent column order
            expected_columns = ['Description', 'Type', 'Qty', 'Amount', 'Date']
            df = df[expected_columns]
            df.to_excel(excel_filename, index=False)
            print(f"\t✔ Saved {len(processed_records)} FILL activities for {target_date} to {excel_filename}")
        
    except Exception as e:
        print(f"Error processing FILL activities: {e}")


def load_weeklytrades_activity(
        file_path: Path = None,
        append: bool = False,
        cumulative_file_path: Path = None):
    """
    Fetch and save all FILL (trade) activities for the current calendar week to Excel.
    Current week is Monday through today (ISO week). Uses the same API as load_trades_activity
    for each day and merges results.

    Args:
        file_path (Path, optional): Custom file path to save the Excel file. If None, uses default path.
        append (bool): If True, append to existing file. If False, overwrite existing file.
        cumulative_file_path (Path, optional): Path to cumulative file. If provided, data will be appended to this file.

    Note:
        Same as load_trades_activity, the API returns up to 100 FILLs per day; days with more are truncated.
    """
    try:
        today = datetime.now().date()
        # Monday of current week (ISO week)
        week_start = today - timedelta(days=today.weekday())
        all_processed_records = []
        expected_columns = ['Description', 'Type', 'Qty', 'Amount', 'Date']

        url = f"{BASE_URL}/v2/account/activities"
        current = week_start
        while current <= today:
            target_date = current.strftime('%Y-%m-%d')
            params = {
                "activity_types": "FILL",
                "limit": 100,
                "date": target_date
            }
            resp = requests.get(url, headers=HEADERS, params=params)
            resp.raise_for_status()
            activities_data = resp.json()
            if activities_data:
                for activity in activities_data:
                    side = activity.get('side', '').upper()
                    qty = float(activity.get('qty', 0))
                    symbol = activity.get('symbol', '')
                    price = float(activity.get('price', 0))
                    transaction_time = activity.get('transaction_time', '')
                    total_value = qty * price
                    try:
                        dt = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
                        local_dt = dt.astimezone()
                        formatted_time = local_dt.strftime('%b %d, %Y, %I:%M:%S %p')
                    except Exception:
                        formatted_time = transaction_time
                    description = f"{side} {qty} {symbol}"
                    all_processed_records.append({
                        'Description': description,
                        'Type': 'FILL',
                        'Qty': float(qty),
                        'Amount': abs(float(total_value)) if side.startswith('SELL') else -abs(float(total_value)),
                        'Date': formatted_time
                    })
            current += timedelta(days=1)

        if not all_processed_records:
            week_end_str = today.strftime('%Y-%m-%d')
            print(f"No FILL activities found for current week ({week_start} to {week_end_str})")
            return

        if file_path is None:
            current_date = datetime.now().strftime('%Y%m%d')
            excel_filename = Path(f"bkp/{TRADING_USERNAME.lower()}/{current_date}-activities_trades_weekly.xlsx")
        else:
            excel_filename = file_path

        excel_filename.parent.mkdir(parents=True, exist_ok=True)

        if cumulative_file_path is not None:
            cumulative_file_path.parent.mkdir(parents=True, exist_ok=True)
            new_df = pd.DataFrame(all_processed_records)[expected_columns]
            if cumulative_file_path.exists():
                existing_cumulative_df = pd.read_excel(cumulative_file_path)
                if set(existing_cumulative_df.columns) == set(expected_columns):
                    existing_cumulative_df = existing_cumulative_df[expected_columns]
                else:
                    print("\t⚠️ Warning: Existing cumulative file has different column structure. Reordering columns.")
                    column_mapping = {}
                    for col in expected_columns:
                        if col in existing_cumulative_df.columns:
                            column_mapping[col] = col
                        else:
                            for existing_col in existing_cumulative_df.columns:
                                if col.lower() in existing_col.lower() or existing_col.lower() in col.lower():
                                    column_mapping[col] = existing_col
                                    break
                    reordered_columns = [column_mapping.get(col, col) for col in expected_columns]
                    existing_cumulative_df = existing_cumulative_df[reordered_columns]
                    existing_cumulative_df.columns = expected_columns
                combined_cumulative_df = pd.concat([existing_cumulative_df, new_df], ignore_index=True)
                combined_cumulative_df.to_excel(cumulative_file_path, index=False)
                print(f"\t✔ Appended {len(all_processed_records)} FILL activities (week {week_start} to {today}) to cumulative file {cumulative_file_path}")
            else:
                new_df.to_excel(cumulative_file_path, index=False)
                print(f"\t✔ Created cumulative file with {len(all_processed_records)} FILL activities (week {week_start} to {today}) at {cumulative_file_path}")

        if append and excel_filename.exists():
            existing_df = pd.read_excel(excel_filename)
            new_df = pd.DataFrame(all_processed_records)[expected_columns]
            if set(existing_df.columns) == set(expected_columns):
                existing_df = existing_df[expected_columns]
            else:
                existing_df = existing_df[expected_columns]
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_excel(excel_filename, index=False)
            print(f"\t✔ Appended {len(all_processed_records)} FILL activities (week {week_start} to {today}) to {excel_filename}")
        else:
            df = pd.DataFrame(all_processed_records)[expected_columns]
            df.to_excel(excel_filename, index=False)
            print(f"\t✔ Saved {len(all_processed_records)} FILL activities (week {week_start} to {today}) to {excel_filename}")

    except Exception as e:
        print(f"Error processing weekly FILL activities: {e}")

def load_dividends_activity(file_path: Path = None):
    """
    Fetch and save DIV (dividend) activities to Excel file using API parameters.
    Gets the latest 100 DIV transactions.
    
    Args:
        file_path (Path, optional): Custom file path to save the Excel file. If None, uses default path.
    """
    try:
        # Fetch DIV activities directly from API with parameters
        url = f"{BASE_URL}/v2/account/activities"
        params = {
            "activity_types": "DIV",
            "limit": 100
        }
        
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        activities_data = resp.json()
        
        # Save raw JSON response as backup
        current_date = datetime.now().strftime('%Y%m%d')
        json_backup_path = Path(f"./alpaca_data2/dividends_raw_{current_date}.json")
        json_backup_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_backup_path, 'w') as f:
            json.dump(activities_data, f, indent=2)
        print(f"\t✔ Saved raw DIV data to {json_backup_path}")
        
        if not activities_data:
            print("No DIV activities found")
            return
        
        # Process each DIV activity
        processed_records = []
        for activity in activities_data:
            # Extract data from activity
            symbol = activity.get('symbol', '')
            qty = float(activity.get('qty', 0))
            net_amount = float(activity.get('net_amount', 0))
            per_share_amount = float(activity.get('per_share_amount', 0))
            # Try different possible field names for transaction time
            transaction_time = activity.get('date')
            
            # Format the transaction time
            try:
                dt = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
                # Convert UTC to local timezone
                local_dt = dt.astimezone()
                formatted_time = local_dt.strftime('%b %d, %Y, %I:%M:%S %p')
            except:
                formatted_time = transaction_time
            
            # Create description
            description = f"DIVIDEND {symbol}"
            
            # Add to processed records
            processed_records.append({
                'Description': description,
                'Type': 'DIV',
                'Quantity': float(qty),
                'Per Share': float(per_share_amount),
                'Net Amount': float(net_amount),
                'Date': formatted_time
            })
        
        # Determine file path
        if file_path is None:
            # Use default path
            current_date = datetime.now().strftime('%Y%m%d')
            excel_filename = Path(f"./{current_date}-activities_dividends.xlsx")
        else:
            # Use custom path
            excel_filename = file_path
        
        # Ensure directory exists
        excel_filename.parent.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(processed_records)
        df.to_excel(excel_filename, index=False)
        
        print(f"\t✔ Saved {len(processed_records)} DIV activities to {excel_filename}")
        
    except Exception as e:
        print(f"Error processing DIV activities: {e}")

def load_fees_activity(file_path: Path = None):
    """
    Fetch and save FEE activities to Excel file using API parameters.
    Gets the latest 100 FEE transactions.
    
    Args:
        file_path (Path, optional): Custom file path to save the Excel file. If None, uses default path.
    """
    try:
        # Fetch FEE activities directly from API with parameters
        url = f"{BASE_URL}/v2/account/activities"
        params = {
            "activity_types": "FEE",
            "limit": 100
        }
        
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        activities_data = resp.json()
        
        # Save raw JSON response as backup
        current_date = datetime.now().strftime('%Y%m%d')
        json_backup_path = Path(f"./alpaca_data2/fees_raw_{current_date}.json")
        json_backup_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_backup_path, 'w') as f:
            json.dump(activities_data, f, indent=2)
        print(f"\t✔ Saved raw FEE data to {json_backup_path}")
        
        if not activities_data:
            print("No FEE activities found")
            return
        
        # Process each FEE activity
        processed_records = []
        for activity in activities_data:
            # Extract data from activity
            symbol = activity.get('symbol', '')
            net_amount = float(activity.get('net_amount', 0))
            description_text = activity.get('description', '')
            # Try different possible field names for transaction time
            transaction_time = activity.get('date')
            
            # Format the transaction time
            try:
                dt = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
                # Convert UTC to local timezone
                local_dt = dt.astimezone()
                formatted_time = local_dt.strftime('%b %d, %Y, %I:%M:%S %p')
            except:
                formatted_time = transaction_time
            
            # Create description
            description = f"FEE {symbol}" if symbol else "FEE"
            
            # Add to processed records
            processed_records.append({
                'Description': description,
                'Type': 'FEE',
                'Details': description_text,
                'Amount': float(-abs(net_amount)) if net_amount < 0 else float(net_amount),
                'Date': formatted_time
            })
        
        # Determine file path
        if file_path is None:
            # Use default path
            current_date = datetime.now().strftime('%Y%m%d')
            excel_filename = Path(f"./{current_date}-activities_fees.xlsx")
        else:
            # Use custom path
            excel_filename = file_path
        
        # Ensure directory exists
        excel_filename.parent.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(processed_records)
        df.to_excel(excel_filename, index=False)
        
        print(f"\t✔ Saved {len(processed_records)} FEE activities to {excel_filename}")
        
    except Exception as e:
        print(f"Error processing FEE activities: {e}")

def load_activities(activities_file_path: str):
    """
    Load activities from JSON file and save FILL records to Excel file.
    
    Args:
        activities_file_path (str): Path to the activities JSON file
    """
    try:
        # Read the activities JSON file
        with open(activities_file_path, 'r') as f:
            activities_data = json.load(f)
        
        # Filter only FILL activities
        fill_activities = [activity for activity in activities_data if activity.get('activity_type') == 'FILL']
        
        if not fill_activities:
            print("No FILL activities found")
            return
        
        # Process each FILL activity
        processed_records = []
        for activity in fill_activities:
            # Extract data from activity
            side = activity.get('side', '').upper()
            qty = float(activity.get('qty', 0))
            symbol = activity.get('symbol', '')
            price = float(activity.get('price', 0))
            transaction_time = activity.get('transaction_time', '')
            
            # Calculate total value
            total_value = qty * price
            
            # Format the transaction time
            try:
                dt = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
                # Convert UTC to local timezone
                local_dt = dt.astimezone()
                formatted_time = local_dt.strftime('%b %d, %Y, %I:%M:%S %p')
            except:
                formatted_time = transaction_time
            
            # Create description
            description = f"{side} {qty} {symbol}"
            
            # Format total value with parentheses for negative (buy) and dollar sign
            if side == 'BUY':
                formatted_value = f"(${total_value:.2f})"
            else:
                formatted_value = f"${total_value:.2f}"
            
            # Add to processed records
            processed_records.append({
                'Description': description,
                'Type': 'FILL',
                'Quantity': float(qty),
                'Value': float(total_value) if side == 'SELL' else float(-total_value),
                'Date': formatted_time
            })
        
        # Create date string for filename
        current_date = datetime.now().strftime('%Y%m%d')
        excel_filename = f"./transactions-alpaca_{current_date}.xlsx"
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(processed_records)
        df.to_excel(excel_filename, index=False)
        
        print(f"\t✔ Saved {len(processed_records)} FILL activities to {excel_filename}")
        
    except FileNotFoundError:
        print(f"Activities file not found: {activities_file_path}")
    except json.JSONDecodeError:
        print(f"Invalid JSON in activities file: {activities_file_path}")
    except Exception as e:
        print(f"Error processing activities: {e}")



def report():
    ### [LOAD] Process activities
    today = datetime.now().strftime('%Y%m%d')
    if (TRADING_USERNAME.lower() == "suntae"): 
        file_path = Path("report/_transaction-Tae.xlsx") # 이모부
    elif (TRADING_USERNAME.lower() == "jaehoon"): 
        file_path = Path("report/_transaction-Jaehoon.xlsx") # Jaehoon
    else:
        print("TRADING_USERNAME not recognized, using default path.")
        file_path = Path("report/_transaction-default.xlsx") # Default path


    load_trades_activity(
        file_path=Path(f"report/{today}-trades.xlsx"),
        cumulative_file_path=file_path
    )
    # load_trades_activity(Path(f"report/{today}-trades.xlsx"))
    # load_trades_activity(Path(f"report/{today}-trades.xlsx"), "2025-06-20")
    load_dividends_activity(Path(f"report/{today}-divs.xlsx"))
    load_fees_activity(Path(f"report/{today}-fees.xlsx"))
    generate_tax_report(file_path)








##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################   fetch
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################

IS_RECESSION = False
IS_DEPRESSION = False
# ─── Helper to GET & save JSON ────────────────────────────────────────────────
def fetch_and_save(endpoint, filename: Path):
    """
    GET /v2/{endpoint}, raise on error, and save the JSON result to `filename`.
    """
    url = f"{BASE_URL}/v2/{endpoint}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()


    filename.parent.mkdir(parents=True, exist_ok=True)

    with open(get_resource(filename,isDebug=True), "w") as f: json.dump(resp.json(), f, indent=2)
    print(f"\t✔ Saved {endpoint} to {filename}")
    
    rows = []
    # Format with date and time
    current_datetime = datetime.now()
    formatted_date = current_datetime.strftime("%Y-%m-%d")
    formatted_time = current_datetime.strftime("%H:%M:%S")
    
        
    # Process data based on endpoint type
    if endpoint == "positions":
        ##### Prep for emergency
        asset_count = 0
        recession_count = 0
        for position in data:
            if (is_bear_etf(position['symbol'])): continue # Skip bear ETFs
            asset_count += 1
            if (float(position['change_today']) < 0): recession_count += 1
        print(
            f"\t[DEBUG]===================================\n"
            f"\trecession_count / asset_count: {recession_count / asset_count}\n"
            f"\t[DEBUG]===================================\n"
            )
        global IS_RECESSION 
        global IS_DEPRESSION 
        IS_RECESSION = (recession_count / asset_count > 0.42)
        IS_DEPRESSION = (recession_count / asset_count > 0.72)


        for position in data:
            # pre-process data ############################ past-data based
            pct_amp = MIN_PCT_AMP * (1.5 if (IS_DEPRESSION) else 1.0)
            frq = 2
            ############################################## current data
            asset = position['symbol']
            if (get_asset_state(asset) == 1): pct_amp = pct_amp * 1.30      #%%%%%%%%%%%%%%% MODEL: Libra
            if (is_bear_etf(asset)): pct_amp = pct_amp * 1.25               ###### bearish etf slowdown (overall market)
            quantity = float(position['qty'])

            if (quantity <= 0): continue # Skip short or zero positions ################## SHORT & ZERO

            market_price = float(position['current_price'])
            qty_unit = round(PURCHASING_POWER / market_price, 2)
            purchase_price = float(position['avg_entry_price'])
            total_profit_and_lose = round((market_price/purchase_price - 1) * 100, 2) # in (%)
            is_profitable = bool(total_profit_and_lose >= (TRIG_DISTROS[3] * pct_amp))
            is_losable = bool(total_profit_and_lose < (TRIG_DISTROS[7] * pct_amp))
            # Debug: print the threshold values and actual value
            print(
                f"[DEBUG] {asset}: "
                f"total_profit_and_lose=( {total_profit_and_lose}% / "
                f"${round(0.01 * total_profit_and_lose * purchase_price * quantity, 2)} ), "
                f"profitable_threshold={round(TRIG_DISTROS[3] * pct_amp,2)}%, "
                f"losable_threshold={round(TRIG_DISTROS[7] * pct_amp,2)}%"
            )
            is_at_mid = not (is_profitable or is_losable)
            is_stocked = (int(quantity) > 0)
            ############################################### normalization + extra logic
            market_price = round(market_price, 2)
            purchase_price = round(purchase_price, 2)


            # For each asset, write or append its position to a CSV file named by symbol.
            csv_path = f"alpaca_data2/position-{asset}.csv"
            headers = [
                "asset",
                "qty_unit",
                "quantity",
                "time",
                "market_price",
                "purchase_price",
                "total_profit_and_lose",
                "is_profitable",
                "is_at_mid",
                "is_losable",
                "is_stocked",
                "pct_amp",
                "frq",
            ]
            file_exists = os.path.isfile(csv_path)
            row = {
                "asset": asset,
                "qty_unit": qty_unit,
                "quantity": quantity,
                "time": formatted_date + " " + formatted_time,
                "market_price": market_price,
                "purchase_price": purchase_price,
                "total_profit_and_lose":total_profit_and_lose,
                "is_profitable": is_profitable,
                "is_at_mid": is_at_mid,
                "is_losable": is_losable,
                "is_stocked": is_stocked,
                "pct_amp": pct_amp,
                "frq": frq,
            }
            rows.append(row)
            with open(csv_path, mode="a", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            print(f"\t✔ Data for {asset} written/appended to {csv_path}")
    elif endpoint == "assets":
        # For assets, we just save the JSON data without processing
        pass
    else:
        print(f"WARNING: Unknown endpoint type: {endpoint}")

    return rows


CURRENT_ASSETS = []
HIGH_DIV_ASSET_BUYS = get_div_asset_list(get_current_week_of_month()) # [LOGIC] high dividend assets
def fetch():
    ### [GET] Fetch orders
    load_orders("alpaca_data2/orders.json")

    fetch_path = Path("alpaca_data2")
    print(f"---- Fetching latest account, assets, and positions from Alpaca API... at {fetch_path} ----")
    
    ### [GET] Account overview (buying power, portfolio value, cash, status…)
    ## 1) Account overview (buying power, portfolio value, cash, status…)
    fetch_and_save("account", fetch_path/Path("account.json"))

    # ## 2) All assets you could trade (status, tradable, marginable…)
    # #    (filter by asset class or status in Python if you like)
    # fetch_and_save("assets", fetch_path/Path("assets.json"))

    ## 3) Open positions (symbol, qty, avg_entry_price, unrealized_pl…)
    rows = fetch_and_save("positions", fetch_path/Path("positions.json"))
    # [LOGIC] Collect all asset symbols in a list
    global CURRENT_ASSETS
    CURRENT_ASSETS = [row['asset'] for row in rows]



    ##### return
    print("\n\n\n")
    return rows



##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################   logic 1 (stock_up_yieldmax)
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
def stock_up_yieldmax(rows):
    # Constants for yieldmax trading
    DIV_PRICE_DISCOUNT = 0.9925        # -0.75% discount for index assets

    print("\n=== STOCK UP YIELD TICKERS ===")
    is_ext_h = is_extended_hours()

    # [LOGIC] High dividend assets not currently held
    high_div_missing = [asset for asset in HIGH_DIV_ASSET_BUYS if asset not in CURRENT_ASSETS]
    # Example usage: Print the two upcoming high dividend asset lists for the current week
    print(
        f"[DEBUG] Your Assets: {CURRENT_ASSETS}\n"
        f"[DEBUG] Dividend Assets: {HIGH_DIVIDEND_ASSETS}\n"
        f"[DEBUG] Dividend Assets to buy (next 2 weeks + this week on Mon and Tue): {HIGH_DIV_ASSET_BUYS}\n"
        f"[DEBUG] High Divs NOT in Assets: {high_div_missing}\n"
    )
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #%%%%%%%%%%%%%%% MODEL: option (YIELDMAX tactic)
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    for asset in high_div_missing:
        # load info
        market_pc = get_price(asset)
        if (market_pc is None): continue
        qty_unit = PURCHASING_POWER / market_pc
        ########################
        print(
            f"  ✓ [YIELD/OPTION] {asset} is missing in your assets, "
            f"stock up logic will be resolved."
        )
        cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
        ###########33
        tgt_qty = qty_unit * 0.85 * (0.5)
        # tgt_qty = qty_unit * 1.70
        tgt_price = market_pc * DIV_PRICE_DISCOUNT
        long_limit_buy(asset, tgt_qty, tgt_price, is_ext_h)
        print(f"  ✓ Limit buy order placed for {asset}")


    ############### DEBUG
    print(f"get_current_week_of_month: {get_current_week_of_month()}")
    print(get_div_asset_list(get_current_week_of_month()))
    for asset in CURRENT_ASSETS:
        if is_last_div(asset):
            print(f"[DEBUG] {asset}: is a dividend asset last week, time to SELL off")
        if is_not_div_sell(asset):
            print(f"[DEBUG] {asset}: is a dividend asset to not SELL")


##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################   logic 1 (stock_up_index) S&P / Russell / Dow Jones / NASDAQ
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
def stock_up_index(rows):
    """
    Place limit buy orders for index assets that are not currently held.
    For each absent index asset, cancel any existing order, calculate the target price and quantity,
    and place a limit buy order (with special handling for certain assets).
    Args:
        rows (list): List of current asset position rows (not used directly here).
    """
    # Constants for index trading
    INDEX_PRICE_DISCOUNT = 0.975        # -2.5% discount for index assets
    INDEX_LIBRA_PRICE_DISCOUNT = 0.961  # -3.9% discount for Libra assets
    
    print("\n=== STOCK UP INDEX TICKERS (S&P / Russell / Dow Jones / NASDAQ) ===")
    is_ext_h = is_extended_hours()
    present_index_assets = [asset for asset in MK_INDEX_ASSETS if asset in CURRENT_ASSETS]
    print(f"[DEBUG] Index Assets ALREADY in Assets: {present_index_assets}\n")
    absent_index_assets = [asset for asset in MK_INDEX_ASSETS if asset not in CURRENT_ASSETS]
    print(f"[DEBUG] Index Assets NOT in Assets: {absent_index_assets}\n")
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #%%%%%%%%%%%%%%% MODEL: Index Libra
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    for asset in absent_index_assets:
        # load info
        market_pc = get_price(asset)
        if (market_pc is None): continue
        qty_unit = round(PURCHASING_POWER / market_pc, 2)
        ########################
        print(
            f"  ✓ [INDEX] {asset} is missing in your assets, "
            f"stock up logic will be resolved."
        )
        cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
        # Calculate target quantity unit
        tgt_qty = qty_unit * 2.20
        tgt_price = market_pc * INDEX_PRICE_DISCOUNT
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        #%%%%%%%%%%%%%%% MODEL: Libra
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if (get_asset_state(asset) == 1): 
            tgt_qty = qty_unit * 0.85 * (0.5)
            tgt_price = market_pc * INDEX_LIBRA_PRICE_DISCOUNT
        
        long_limit_buy(asset, tgt_qty, tgt_price, is_ext_h)
        print(f"  ✓ [INDEX] Limit buy order placed for {asset}\n")


    # for row in rows:
    #     # Load each field from the row using their variable names
    #     asset, qty_unit, quantity, market_pc = row['asset'], row['qty_unit'], row['quantity'], row['market_price']
    #     if asset not in present_index_assets: continue
    #     if (quantity > (qty_unit * 7.49)): continue # (>7.49): skip  !!!!!!!!!!!!!!!!!!! 7 units is at decent risk
    #     ########################
    #     print(
    #         f"  ✓ [INDEX] {asset} is already in your assets and not enough, "
    #         f"extra stock up logic will be resolved."
    #     )
    #     cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
    #     ###################
    #     # Calculate target quantity unit
    #     tgt_qty = qty_unit * 0.85
    #     tgt_price = market_pc * INDEX_PRICE_DISCOUNT
    #     #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #     #%%%%%%%%%%%%%%% MODEL: Libra
    #     #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #     if (get_asset_state(asset) == 1):
    #         tgt_qty = qty_unit * 0.85 * (0.5)
    #         tgt_price = market_pc * INDEX_LIBRA_PRICE_DISCOUNT

    #     long_limit_buy(asset, tgt_qty, tgt_price,is_ext_h)
    #     print(f"    ✓ Limit buy order placed for {asset}\n")





##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################   logic 2 (Trading)
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################
##################################################################################

def trading_logic(rows):
    print("\n=== TRADING LOGIC ===")
    print(f"Processing {len(rows)} assets...")
    is_ext_h = is_extended_hours()
    
    for row in rows:
        # Load each field from the row using their variable names
        asset = row['asset']
        qty_unit = row['qty_unit']
        quantity = row['quantity']
        time_val = row['time']
        market_price = row['market_price']
        purchase_price = row['purchase_price']
        total_profit_and_lose = row['total_profit_and_lose']
        is_profitable = row['is_profitable']
        is_at_mid = row['is_at_mid']
        is_losable = row['is_losable']
        is_stocked = row['is_stocked']
        pct_amp = row['pct_amp']
        frq = row['frq']


        time.sleep(0.1)
        

        # ###### DEBUG
        # ############################################## state decision
        # if total_profit_and_lose    >= TRIG_DISTROS[0] * pct_amp:   _state,state = 0,f"[0]Very High ({total_profit_and_lose}%)"
        # elif total_profit_and_lose  >= TRIG_DISTROS[1] * pct_amp:   _state,state = 1,f"[1]High ({total_profit_and_lose}%)"
        # elif total_profit_and_lose  >= TRIG_DISTROS[2] * pct_amp:   _state,state = 2,f"[2]Moderately High ({total_profit_and_lose}%)"
        # elif total_profit_and_lose  >= TRIG_DISTROS[3] * pct_amp:   _state,state = 3,f"[3]Medium ({total_profit_and_lose}%)"

        # elif total_profit_and_lose  >= TRIG_DISTROS[4] * pct_amp:   _state,state = 4,f"[4]Neutral ({total_profit_and_lose}%)"
        # elif total_profit_and_lose  >= TRIG_DISTROS[5] * pct_amp:   _state,state = 5,f"[5]Medium Low ({total_profit_and_lose}%)"

        # elif total_profit_and_lose  >= TRIG_DISTROS[6] * pct_amp:   _state,state = 6,f"[6]Moderately Low ({total_profit_and_lose}%)"
        # elif total_profit_and_lose  >= TRIG_DISTROS[7] * pct_amp:   _state,state = 7,f"[7]Low ({total_profit_and_lose}%)"
        # elif total_profit_and_lose  >= TRIG_DISTROS[8] * pct_amp:   _state,state = 8,f"[8]Low ({total_profit_and_lose}%)"
        # else:                                                       _state,state = 9,f"[9]Very Low ({total_profit_and_lose}%)"
        # print(f"{asset} = {state}")
        # ############################################## state decision 2
        # if is_profitable and (not is_stocked):  print(f"  [MARKET-BUY / UP-BLANACE]...state: {_state}")
        # elif is_profitable:                     print(f"  [LIMIT-SELL]...state: {_state}")
        # elif is_at_mid:                         print(f"  [NONE]...state: {_state}")
        # elif is_losable:                        print(f"  [LIMIT-BUY / DOWN-BLANACE]...state: {_state}")
        # ############################################## state decision 3 (Libra Model)
        # if (get_asset_state(asset) == 0): 
        #     print(f"\t•   Normal Asset (No ETF).")
        # if (get_asset_state(asset) == 1): 
        #     print(f"\t•   {asset} is a etf (bull/bear) registered (ETF BULL/BEAR).")
        # if (get_asset_state(asset) == 2):
        #     print(f"\t•   {asset} is Base of ETF (ETF BASE).")
        #     etfs = get_equiv_asset_etf(asset_symbol=asset)
        #     for etf in etfs:
        #         etf_lev = etf['leverage'] # >0 == bull, <0 == bear
        #         etf_asset = etf['ticker']
        #         etf_price = get_price(etf_asset)
        #         etf_qty_unit = int(PURCHASING_POWER / etf_price + 0.5)
        #         if (etf_lev > 0 
        #             # and etf_asset not in CURRENT_ASSETS
        #             ): 
        #             print(f"\t\t•   {etf_asset} is a bull {etf_qty_unit}@{etf_price}, not in current asset")
        #         if (etf_lev < 0 
        #             # and etf_asset not in CURRENT_ASSETS
        #             ): 
        #             print(f"\t\t•   {etf_asset} is a bear {etf_qty_unit}@{etf_price}, not in current asset")
        # print('\n\n')
        # continue



        
        ###########################################################################
        ###########################################################################
        ######################## Liquidation Logic 
        ###########################################################################
        ###########################################################################
        if (
            (asset in HIGH_DIVIDEND_ASSETS) and 
            (quantity >= (qty_unit * 40.0)) and 
            (-6.0 <= total_profit_and_lose and total_profit_and_lose <= 0.0)
            ): 
            print(f"  → [LIQUIDATE]: Selling {asset}, non-liquid asset (stock shares) into a liquid asset (cash)")
            cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
            tgt_qty = quantity
            tgt_price = purchase_price * 1.005
            long_limit_sell(asset, tgt_qty, tgt_price, is_ext_h)
            continue
        
        ###########################################################################
        ###########################################################################
        ######################## Market Logic 
        ###########################################################################
        ###########################################################################
        # if is_profitable and (not is_stocked):  print(f"  [MARKET-BUY / UP-BLANACE]...state: {_state}")
        if is_profitable and (not is_stocked):
            print(f"  → ACTION: Market buy (profitable but not stocked)")
            cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
            discounted_rate = 0.995
            tgt_price = market_price * discounted_rate
            tgt_qty = qty_unit * 0.85 * (0.5) - quantity # 50% of the quantity unit for tracking
            if (tgt_qty <= 0): 
                print(f"  → DECIDED: fractionally stocked, moving on...")
                is_profitable = True # quantity is large enough
            else:
                long_limit_buy(asset,tgt_qty,tgt_price,isExtHour=is_ext_h)
                print(f"    ✓ Market buy (limit & extended hour) order placed for {asset}")
                continue ## need to give extra time to re-blanace
        ##-------------------------------------------------------------------
        # if is_profitable:                       print(f"  [LIMIT-SELL]...state: {_state}")
        if is_profitable:
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            #%%%%%%%%%%%%%%% MODEL: option (YIELDMAX tactic)
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            if is_not_div_sell(asset):
                if(total_profit_and_lose > 3.75): 
                    print(f"  → [OPTION-SPECIAL]: Selling (profitable over dividend)")
                    cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
                    if (is_ext_h or IS_RECESSION):
                        tgt_price = purchase_price * (1 + 0.01*(total_profit_and_lose + 0.25))
                        long_limit_sell(asset, quantity, tgt_price, is_ext_h)
                    else:
                        tgt_price = purchase_price * (1 + 0.01*(total_profit_and_lose - 0.75))
                        long_stop_sell(asset, quantity, tgt_price)
                continue

            print(f"  → ACTION: Selling (profitable)")
            cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
            ##################3
            tgt_qty = quantity
            ##################3
            if (is_ext_h or IS_RECESSION): 
                tgt_price = purchase_price * (1 + 0.01*(total_profit_and_lose * LIMIT_OFFSET_RATE))
                long_limit_sell(asset, tgt_qty - 0.01, tgt_price, is_ext_h)
                print(f"    ✓ Limit sell (decided) order placed for {asset}")
            else:
                tgt_price = purchase_price * (1 + 0.01*(total_profit_and_lose * STOPP_OFFSET_RATE))
                long_stop_sell(asset, tgt_qty - 0.01, tgt_price)
                print(f"    ✓ Stop sell (decided) order placed for {asset}")


        # ##-------------------------------------------------------------------
        if is_at_mid:
            print(f"  → ACTION: No action (at mid-range)")
            print(f"    Asset {asset} is in neutral territory, minimizing libra and option ETF risk")
            MIN_PROFIT_RATE_LIBRA=1.018     # 1.8%
            MAX_PROFIT_RATE_LIBRA=1.036     # 3.6%
            MIN_PROFIT_RATE_OPTION=1.008    # 0.8%
            if ((get_asset_state(asset) == 1) and total_profit_and_lose < -3.33): 
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                #%%%%%%%%%%%%%%% MODEL: Libra
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
                tgt_qty = quantity
                tgt_price = purchase_price * MIN_PROFIT_RATE_LIBRA
                long_limit_sell(asset, tgt_qty, tgt_price, is_ext_h)

            elif ((get_asset_state(asset) == 1) and total_profit_and_lose >= -3.33): 
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                #%%%%%%%%%%%%%%% MODEL: Libra
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
                tgt_qty = quantity
                tgt_price = purchase_price * MAX_PROFIT_RATE_LIBRA
                long_limit_sell(asset, tgt_qty, tgt_price, is_ext_h)

            elif (is_last_div(asset) and total_profit_and_lose < 0 or asset in EXPIRED_DIVIDEND_ASSETS): 
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                #%%%%%%%%%%%%%%% MODEL: option (YIELDMAX tactic)
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
                tgt_qty = quantity
                tgt_price = purchase_price * MIN_PROFIT_RATE_OPTION
                long_limit_sell(asset, tgt_qty, tgt_price, is_ext_h)

            elif (is_last_div(asset) and total_profit_and_lose >= 0 or asset in EXPIRED_DIVIDEND_ASSETS): 
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                #%%%%%%%%%%%%%%% MODEL: option (YIELDMAX tactic)
                #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
                tgt_qty = quantity
                tgt_price = market_price * MIN_PROFIT_RATE_OPTION
                long_limit_sell(asset, tgt_qty, tgt_price, is_ext_h)


        # ##-------------------------------------------------------------------
        # if is_losable:                          print(f"  [LIMIT-BUY / DOWN-BLANACE]...state: {_state}")
        if is_losable:
            print(f"  → ACTION: Limit buy (losable)")
            cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
            ###################################
            if   (quantity < (qty_unit * 0.90)):tgt_qty = qty_unit * 1.10 - quantity    # (1):  E(X) == x1.00
            elif (quantity < (qty_unit * 1.80)):tgt_qty = qty_unit * 2.20 - quantity    # (2):  E(X) == x2.00
            elif (quantity < (qty_unit * 7.99)):tgt_qty = quantity * 2.50               # (3,4):E(X) == x7.00
            else:                               tgt_qty = qty_unit * 3.50               # (>5): buy-gravity
            
            normalized_pnl = min(get_mean_pnl(asset),total_profit_and_lose) ## gravity
            pnl_multiplier=(1 + 0.01*(normalized_pnl * LIMIT_OFFSET_RATE))
            pnl_multiplier=min(pnl_multiplier, 0.95) ######### special logic for buying (at least @-5%)
            tgt_price = purchase_price * pnl_multiplier

            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            #%%%%%%%%%%%%%%% MODEL: option (YIELDMAX tactic)
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            if(asset in EXPIRED_DIVIDEND_ASSETS): tgt_price = tgt_price *0.97

            long_limit_buy(asset, tgt_qty, tgt_price,is_ext_h)
            print(f"    ✓ Limit buy order placed for {asset}")
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            #%%%%%%%%%%%%%%% MODEL: Libra
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            if (get_asset_state(asset) == 2):
                print(f"    → Checking Libra ETF pairs for {asset}...")
                etfs = get_equiv_asset_etf(asset_symbol=asset)
                for etf in etfs:
                    etf_lev = etf['leverage'] # (> 0) == bull, (< 0) == bear
                    etf_asset = etf['ticker']
                    etf_price = get_price(etf_asset)
                    if (etf_price is None): continue
                    etf_qty_unit = PURCHASING_POWER / etf_price
                    etf_tgt_qty = etf_qty_unit * 0.85 * (0.5)
                    etf_tgt_price = etf_price * 0.98 # -2% discount for ETF assets
                    if (etf_lev > 0 and etf_asset not in CURRENT_ASSETS):                   # (> 0) == bull
                        cancel_order_by_asset(etf_asset, "alpaca_data2/orders.csv")
                        long_limit_buy(etf_asset,etf_tgt_qty,etf_tgt_price,is_ext_h)
                        print(f"        ✓ Limit buy order placed for {etf_asset}")
                    if (etf_lev < 0 and etf_asset not in CURRENT_ASSETS and IS_RECESSION):  # (< 0) == bear
                        cancel_order_by_asset(etf_asset, "alpaca_data2/orders.csv")
                        long_limit_buy(etf_asset,etf_tgt_qty,etf_tgt_price,is_ext_h)
                        print(f"        ✓ Limit buy order placed for {etf_asset}")





def liquidate(rows, rate=1.013, targets=[], excludes=[]):
    """
    Liquidate all positions by selling them at market price.
    This function cancels all orders and sells all assets in the portfolio.
    """
    print("Liquidating all positions...")
    cancel_all_orders_in("alpaca_data2/orders.csv")
    for row in rows:
        if row['asset'] not in targets: continue
        if row['asset'] in excludes: continue
        qty_to_sell = row['quantity'] if row['asset'] in NONFRACT_ASSETS else row['quantity'] - 0.01
        if (row['total_profit_and_lose'] < 0 and qty_to_sell > 0): #1.003 / 1.013
            long_limit_sell(row['asset'], qty_to_sell, row['purchase_price'] * rate, isExtHour=True)
        if (row['total_profit_and_lose'] >= 0 and qty_to_sell > 0):
            long_limit_sell(row['asset'], qty_to_sell, row['market_price'] * rate, isExtHour=True)






def rebalance(rows, pct_discount=None, target_pnl=None, is_bullish=True, bound=0):
    """
    Rebalance portfolio by buying more of any asset with total_profit_and_lose below a threshold.
    Uses similar logic to the 'losable' case in trading_logic.

    Args:
        rows (list): List of asset position rows.
        pct_discount (float, optional): Percent discount for lower buying price. Defaults to 3 if None.

    Usage:
        rebalance(rows)                     # Example: Rebalance with default discount (3%)
        rebalance(rows, pct_discount=5.0)   # Example: Rebalance with a custom discount (e.g., 5%)
        rebalance(rows, pct_discount=7.0)   # Example: Rebalance with a custom discount (e.g., 7%)
        rebalance(rows, pct_discount=9.0)   # Example: Rebalance with a custom discount (e.g., 9%)
        rebalance(rows, pct_discount=9.0, target_pnl=-15.0)   # Example: Rebalance with discount for target pnl (e.g., 9%)
    """

    if pct_discount is None: pct_discount = 3.0  # default percent discount
    if target_pnl is None: target_pnl = -17.0

    print("\n=== REBALANCE LOGIC ===")
    is_ext_h = is_extended_hours()
    for row in rows:
        asset = row['asset']
        qty_unit = row['qty_unit']
        quantity = row['quantity']
        if (qty_unit * quantity > bound): continue  # skip over-bound assets
        purchase_price = row['purchase_price']
        total_profit_and_lose = row['total_profit_and_lose']
        # Skip assets with PnL above the threshold
        if total_profit_and_lose > target_pnl: continue
        if (is_bullish and is_bear_etf(asset)): continue               # skip bearish etf in bullish market
        if ((not is_bullish) and (not is_bear_etf(asset))): continue   # skip bullish etf in bearish market
        #########################
        print(f"  → REBALANCE: Buying more of {asset} (PnL={total_profit_and_lose}%)")
        cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
        # Determine target quantity based on current holding
        #.......................................................................... # skipping (1):  E(X) == x1.00
        if   (quantity < (qty_unit * 1.80)):tgt_qty = qty_unit * 2.20 - quantity    # (2):  E(X) == x2.00
        elif (quantity < (qty_unit * 7.99)):tgt_qty = quantity * 2.50               # (3,4):E(X) == x7.00
        else:                               tgt_qty = qty_unit * 5.00               # (>5): buy-gravity
        
        # Add pct_discount to normalized_pnl for lower buying price
        pnl_multiplier = 1 + 0.01 * (total_profit_and_lose - pct_discount)
        tgt_price = purchase_price * pnl_multiplier
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        #%%%%%%%%%%%%%%% MODEL: option (YIELDMAX tactic)
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if(asset in EXPIRED_DIVIDEND_ASSETS): tgt_price = tgt_price *0.97


        #### exception
        if (tgt_price < 3.00): tgt_price -= 0.01 # get rid of offset

        long_limit_buy(asset, tgt_qty, tgt_price, is_ext_h)
        print(f"    ✓ Limit buy order placed for {asset}")














def get_cash_equity_ratio():
    """
    Parse alpaca_data2/account.json, compare 'cash' and 'equity',
    and return True if cash > 0.90 * equity, else False.

        if (get_cash_equity_ratio() < 0.24):  
            # < 24% (No Cash to Automate)
        if (get_cash_equity_ratio() > 0.70):  
            # > 70% (Enough to stock up)
    """
    account_path = Path("alpaca_data2/account.json")
    if not account_path.exists():
        raise FileNotFoundError(f"Account file not found: {account_path}")
    with account_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        cash = float(data["cash"])
        equity = float(data["equity"])
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Invalid or missing 'cash' or 'equity' in account.json: {e}")
    return (cash / equity)




def get_mean_pnl(asset: str) -> float:
    """
    Read the last 4 rows from position-{asset}.csv and calculate the mean of total_profit_and_lose.
    If less than 4 rows exist, return the last total_profit_and_lose.
    
    Args:
        asset (str): The asset symbol
        
    Returns:
        float: Mean of last 4 market prices, or last market price if less than 4 rows
    """
    csv_path = Path(f"alpaca_data2/position-{asset}.csv")
    if not csv_path.exists(): raise FileNotFoundError(f"Position file not found: {csv_path}")
    
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows: raise ValueError(f"No data found in {csv_path}")
    
    # Get the last 4 rows (or all rows if less than 4)
    last_rows = rows[-4:] if len(rows) >= 4 else rows
    
    # Extract market prices and calculate mean
    total_profit_and_loses = [float(row['total_profit_and_lose']) for row in last_rows]
    mean_pnl = sum(total_profit_and_loses) / len(total_profit_and_loses)
    
    return round(mean_pnl, 2)





























"""
Utility functions for managing a shutdown flag via a file (flag.txt).
This allows external processes, background jobs, or administrators to 
signal the running service to exit gracefully.

Functions:
----------
write_check(value: bool) -> None
    Write a boolean value ("True" or "False") into flag.txt.
    Used to request shutdown (True) or clear the shutdown request (False).

    Usage examples:
    --------------
    >>> write_check(True)   # Signal service to shut down
    >>> write_check(False)  # Reset the flag, continue running

read_check() -> None
    Read flag.txt, check if it contains "true". If so, raise SystemExit 
    to terminate the program gracefully. If the file does not exist, 
    it is ignored.

    Usage examples:
    --------------
    >>> while True:
    ...     time.sleep(1)
    ...     read_check()   # Will exit the loop if flag.txt == "True"

Typical workflow:
-----------------
1. Service runs a main loop that periodically calls `read_check()`.
2. To stop the service, another process (or user) calls `write_check(True)`.
3. On the next cycle, `read_check()` raises SystemExit, caught by the 
   main loop's exception handler, which performs cleanup and exits.
4. Optional: reset the flag with `write_check(False)` before restarting 
   the service.
"""
def write_check(value: bool) -> None:
    with open("flag.txt", "w") as f:
        f.write("True" if value else "False")

def read_check():
    # Check the flag file
    try:
        with open("flag.txt", "r") as f:
            flag = f.read().strip().lower()
        if flag == "true": return True
        else: return False
    except FileNotFoundError:
        return False







def index_logic():
    ################ 4 U.S. representitive index trading logic here!
    rows=fetch()
    if (IS_DEPRESSION): 
        cancel_all_orders_in("alpaca_data2/orders.csv")
        rebalance(rows, pct_discount=9.0)   # Example: Rebalance with a custom discount (e.g., 9%)
        write_check(True)
    if (read_check()): 
        print("Shutdown flag detected. Exiting...")
        return
    
    if (get_cash_equity_ratio() > 0.42 and not IS_DEPRESSION): stock_up_index(rows)
    if (get_cash_equity_ratio() < 0.06 and not IS_DEPRESSION): liquidate(rows) # < 08% (No Cash to Automate)


def logic():
    ################ trading logic here!
    rows=fetch()
    if (IS_DEPRESSION): 
        cancel_all_orders_in("alpaca_data2/orders.csv")
        rebalance(rows, pct_discount=9.0)   # Example: Rebalance with a custom discount (e.g., 9%)
        write_check(True)
    if (read_check()): 
        print("Shutdown flag detected. Exiting...")
        return
    

    print(f"Cash/Equity Ratio: {get_cash_equity_ratio():.4f}")
        
    if (get_cash_equity_ratio() > 0.18 and not IS_DEPRESSION): stock_up_yieldmax(rows)
    if (get_cash_equity_ratio() > 0.06 and not IS_DEPRESSION): trading_logic(rows)
    if (get_cash_equity_ratio() < 0.06 and not IS_DEPRESSION): liquidate(rows) # < 08% (No Cash to Automate)










def manual_short(asset=None, dollars=None, extra_buy_asset=None, is_double_scaled=False):
    price_target = get_price(asset)
    quantity = math.ceil(1.8 * PURCHASING_POWER / price_target)
    if (price_target is None): 
        print(f"  ✗ [DEBUG] {asset} price not found, skipping manual short.")
        return
    
    load_orders("alpaca_data2/orders.json")
    cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
    time.sleep(0.5)
    if (extra_buy_asset is not None): 
        cancel_order_by_asset(extra_buy_asset, "alpaca_data2/orders.csv")
        time.sleep(0.5)

    exists_asset = False
    is_more_short = False
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    for position in data:
        if ((position['symbol'] == asset and float(position['qty']) < 0)):
            exists_asset = True
            price_target = min(float(position['current_price']), float(position['avg_entry_price']))
            is_more_short = float(position['current_price']) > (float(position['avg_entry_price']) * 0.975) # >= +2.5%
            quantity = abs(float(position['qty'])) # buy all quantity
            if (is_more_short): 
                exists_asset = False # force additional sell
                price_target = max(float(position['current_price']), float(position['avg_entry_price']))
                quantity *= 2.2

    short_sell_rate = 1.084 # 8.4% above (short sell)
    finish_buy_rate = 0.976 # 2.4% below (buy, finish the short position)
    long_transition_rate = 0.965 # 3.5% below (buy, switch to long)
    if (is_double_scaled): 
        short_sell_rate = 1.125 # 12.5% above (short sell)
        finish_buy_rate = 0.964 # 3.6% below (buy, finish the short position)
        long_transition_rate = 0.930 # 7.0% below (buy, switch to long)
    

    if (not exists_asset):
        long_limit_sell(asset, quantity, price_target * short_sell_rate, isExtHour=True)  
        print(f"\033[91m  ✓ [DEBUG] {asset} (1) {"MORE" if is_more_short else ""} short sell order placed.\033[0m")
        print(f"    → Status...")
        print(f"      exists_asset = {exists_asset}")
        print(f"      price_target = {price_target}")
        print(f"      quantity = {quantity}")
    else:
        long_limit_buy(asset, quantity, price_target * finish_buy_rate, isExtHour=True)
        print(f"\033[92m  ✓ [DEBUG] {asset} (2) buy order (after short sell) placed.\033[0m")
        print(f"    → Status...")
        if (extra_buy_asset is not None):
            etf_price = get_price(extra_buy_asset)
            etf_tgt_qty = PURCHASING_POWER / etf_price * (0.5)
            long_limit_buy(extra_buy_asset, etf_tgt_qty, etf_price * long_transition_rate, isExtHour=True) 
            print(f"\033[92m  ✓ [DEBUG] {asset} (3) extra buy (reversing position) order placed.\033[0m")

# Colors
# Red: \033[91m
# Green: \033[92m
# Yellow: \033[93m
# Blue: \033[94m





def short_operation(is_checking=False, is_double_scaled=False):
    dollar_amont = PURCHASING_POWER * 10
    short_assets_with_extra = {
        ############## Software
        "YOU": None,            # 6.16 B *** (Key asset to rip off)************************
        "COHR": None,           # 46.03 B
        ############## Wearables & Essential Goods
        "FIGS": None,           # 2.73 B *** (Key asset to rip off)************************
        # "CAVA": None,           # 9.15 B
        ############## Healthcare
        # "NTLA": None,           # 1.59 B
        # "TWST": None,           # 2.88 B
        
        ############## Networking
        "AAOI": None,           # 7.19 B *** (Key asset to rip off)************************



        ############## Quntum Computing
        # "RGTI": None,           # 5.81  B
        "QBTS": None,           # 7.84  B *** (Key asset to rip off)************************
        # "IONQ": None,           # 12.57 B



        ############## Aerospace & Defense
        "RCAT": None,           # 1.75 B *** (Key asset to rip off)************************
        # "RDW": None,            # 1.67  B 
        "ONDS": None,            # 4.50 B *** (Key asset to rip off)************************
        "PL": None,             # 8.19  B *** (Key asset to rip off)************************
        # "AVAV": None,           # 11.35 B
        "KTOS": None,           # 16.68 B *** (Key asset to rip off)************************
        "ASTS": None,           # 37.81 B *** (Key asset to rip off)************************
        # "RKLB": None,           # 40.51 B

        # "JOBY": "JOBX",         # 10.37 B



        ############## Energy
        # "NNE": None,            # 1.44  B 
        # "EOSE": None,           # 4.29  B 
        # "SMR": None,            # 5.35  B 
        # "OKLO": None,           # 11.73  B *** (Key asset to rip off)************************
        "BE": None,             # 43.45  B *** (Key asset to rip off)************************

        # "CRML": None,           # 1.26  B 



        ############## Semiconductor
        "AEHR": None,           # 0.84  B *** (Key asset to rip off)************************
        "SKYT": None,           # 1.47  B *** (Key asset to rip off)************************
        # "NVTS": None,           # 2.13  B
        "APLD": None,           # 10.70 B *** (Key asset to rip off)************************
    }
    if (not is_checking): short_finishing() 
    ######### MANUAL SHORTING (SELL and BUY automatically decided everytime)
    if (not is_checking):
        for asset, extra_buy_asset in short_assets_with_extra.items():
            manual_short(asset, dollar_amont, extra_buy_asset=extra_buy_asset, is_double_scaled=is_double_scaled)
    else:
        url = f"{BASE_URL}/v2/positions"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        is_no_short = True
        for position in data:
            if (position['symbol'] in short_assets_with_extra.keys() or float(position['qty']) < 0):
                print(f"\033[93m  ✓ [REPORT] {position['symbol']} is in short\033[0m")
                print(f"    → qty = {position['qty']}, ")
                print(f"      avg_entry_price = {position['avg_entry_price']}, ")
                print(f"      current_price = {position['current_price']}, ")
                print(f"      unrealized_plpc = {position['unrealized_plpc']}, ")
                print(f"      %plpc = {float(position['unrealized_plpc']) * 100:.2f}%")
                is_no_short = False
        if (is_no_short):
            print(f"\033[92m  ✓ [REPORT] No short positions found...\033[0m")




def short_finishing():
    """
    Close all short positions (negative quantity) by placing limit buy orders
    at min(market_price, entry_price) * 0.995.
    """
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    positions = resp.json()

    short_positions = [p for p in positions if float(p["qty"]) < 0]
    if not short_positions:
        print(f"  ✓ [short_finishing] No short positions to close.")
        return

    load_orders("alpaca_data2/orders.json")
    for p in short_positions:
        sym = p["symbol"]
        qty = float(p["qty"])
        close_qty = abs(qty)
        avg_entry_price = float(p["avg_entry_price"])
        current_price = float(p["current_price"])
        limit_price = min(current_price, avg_entry_price) * 0.993
        cancel_order_by_asset(sym, "alpaca_data2/orders.csv")
        time.sleep(0.2)
        print(f"  → [short_finishing] Closing short {sym}: buy {close_qty} @ ${limit_price:.2f} (min(market,entry)*0.993)")
        long_limit_buy(sym, close_qty, limit_price, isExtHour=True)







INDICES = [
    'GDXU', 'SLV','COPX','LIT', # minings
    'SPXL', 'SSO', 'SPY', # essentials
    'TQQQ', 'QLD', 'QQQ', 'QQQM', 'QQQU', # Tech
    'UDOW', 'DDM', 'DIA', # dow johns
    'TNA',  'URTY', 'IWM', # russell 2000
    'JEPI', 'JEPQ', 'SCHD', # accumulative assets
    'GBTC', 'BTC', 'ETHE', 'ETH', # crypto
    'AIQ', 'UFO', 'QTUM', # future
    'BUG', 'CHAT', 'IGV', 'IGPT', 'AOTS', # software
]
def modern_logic():
    # load_orders("alpaca_data2/orders.json")
    # cancel_order_by_asset(asset, "alpaca_data2/orders.csv")
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    # Modern logic: Covered-Call entry buy

    # Modern logic: Long position management
    for p in data:
        ticker = p['symbol']
        cancel_order_by_asset(ticker, "alpaca_data2/orders.csv")
        qty = float(p['qty'])
        avg_entry_price = float(p['avg_entry_price'])
        current_price = float(p['current_price'])
        unrealized_plpc = float(p['unrealized_plpc'])
        rebalance_rate = GET_RATE(unrealized_plpc)
        rebalance_price = min(current_price, avg_entry_price) * rebalance_rate
        if (get_asset_state(ticker) == 1): rebalance_price *= 0.95 # 5% discount for high volatility
        short_rebalance_price = min(current_price, avg_entry_price) * 0.965
        pct_plpc = unrealized_plpc * 100
        daily_plpc = float(p['change_today'])
        pct_daily_plpc = daily_plpc * 100
        market_value = qty * current_price

        
        tgt_qty = PURCHASING_POWER / current_price * 0.5 if (market_value > 2 * PURCHASING_POWER or qty == 0.01) else qty * 3.0
        if ticker in INDICES and market_value > 2 * PURCHASING_POWER: tgt_qty = PURCHASING_POWER / current_price

        # sell
        if (qty >= 0 and pct_plpc > 0 and pct_daily_plpc > 7.0): # profitable position (and daily gain is over 7%)
            if (qty > 0.01): # stocked long
                print(f"[STOCKED LONG] position: {ticker} is profitable and daily gain is over 7%...")
            else: # unstocked long
                print(f"[UNSTOCKED LONG] position: {ticker} is profitable and daily gain is over 7%...")

        
        if (qty < 0 and pct_plpc > 0 and pct_daily_plpc > 7.0): # profitable position (and daily gain is over 7%)
            print(f"[SHORT] position: {ticker} is profitable and daily gain is over 7%...")
        

        if (get_cash_equity_ratio() < 0.18): continue

        # INDICES buy
        if (qty >= 0 and ticker in INDICES and pct_daily_plpc >= -3.0):
            print(f"[INDICES] position: {ticker} is TODAY no change...")
            continue
        if (qty >= 0 and ticker in INDICES and pct_daily_plpc < -3.0):
            print(f"[INDICES] position: {ticker} is TODAY losing more than 3.0%...")
            print(f"    → pct_plpc: {pct_plpc:.2f}%")
            print(f"    → pct_daily_plpc: {pct_daily_plpc:.2f}%")
            print(f"    → qty: {qty}")
            print(f"    → market_value: ${market_value:.2f}")
            print(f"    -------------------------------------------")
            print(f"    → avg_entry_price: ${avg_entry_price:.2f}")
            print(f"    → current_price: ${current_price:.2f}")
            print(f"    → tgt_qty: {tgt_qty}")
            print(f"    → estimated rebalance value: ${current_price * 0.985 * tgt_qty:.2f}")
            print(f"    -------------------------------------------")
            long_limit_buy(ticker, tgt_qty, current_price * 0.985, isExtHour=True)
            continue
        # buy
        if (qty >= 0 and pct_plpc < -33.0):
            if (ticker in HOLD_ASSETS): continue
            if (ticker in HIGH_DIVIDEND_ASSETS and -50.0 < pct_plpc): continue # loss must be more than 50%, for high dividend assets
            print(f"[LONG] position: {ticker} is losing more than 33%...")
            print(f"    → pct_plpc: {pct_plpc:.2f}%")
            print(f"    → pct_daily_plpc: {pct_daily_plpc:.2f}%")
            print(f"    → qty: {qty}")
            print(f"    → market_value: ${market_value:.2f}")
            print(f"    -------------------------------------------")
            print(f"    → avg_entry_price: ${avg_entry_price:.2f}")
            print(f"    → current_price: ${current_price:.2f}")
            print(f"    → tgt_qty: {tgt_qty}")
            print(f"    → rebalance_price: ${rebalance_price:.2f}")
            print(f"    → estimated rebalance value: ${rebalance_price * tgt_qty:.2f}")
            print(f"    -------------------------------------------")
            long_limit_buy(ticker, tgt_qty, rebalance_price, isExtHour=True)
            continue
        

        # short
        # if (qty < 0):
        #     print(f"[SHORT] position: {ticker} is in short...")
        #     print(f"    → pct_plpc: {pct_plpc:.2f}%")
        #     print(f"    → pct_daily_plpc: {pct_daily_plpc:.2f}%")
        #     print(f"    → qty: {qty}")
        #     print(f"    → market_value: ${market_value:.2f}")
        #     print(f"    -------------------------------------------")
        #     print(f"    → avg_entry_price: ${avg_entry_price:.2f}")
        #     print(f"    → current_price: ${current_price:.2f}")
        #     print(f"    → tgt_qty: {abs(qty)}")
        #     print(f"    → short_rebalance_price: ${short_rebalance_price:.2f} (3.5% below)")
        #     print(f"    → estimated market value to close: ${short_rebalance_price * abs(qty):.2f}")
        #     print(f"    -------------------------------------------")
            # long_limit_buy(ticker, abs(qty), short_rebalance_price, isExtHour=True)

        # print(f"position: {ticker}")
        # print(f"qty: {qty}")
        # print(f"avg_entry_price: {avg_entry_price}")
        # print(f"current_price: {current_price}")
        # print(f"current_market_value: {current_market_value}")
        # print(f"%plpc: {unrealized_plpc * 100:.2f}%")
        # print(f"%daily_plpc: {pct_daily_plpc:.2f}%")

#     is_found = False
#     for position in data:
#         if (position['symbol'] == asset):
#             is_found = True
#             is_sell = float(position['current_price']) > (float(position['avg_entry_price']) * 1.0299) # +2.99%
#             print(f"\033[93m  ✓ [REPORT] {position['symbol']} is in position\033[0m")
#             print(f"    → qty = {position['qty']}, ")
#             print(f"      avg_entry_price = {position['avg_entry_price']}, ")
#             print(f"      current_price = {position['current_price']}, ")
#             print(f"      unrealized_plpc = {position['unrealized_plpc']}, ")
#             print(f"      %plpc = {float(position['unrealized_plpc']) * 100:.2f}%")
#             # additional buy
#             if (is_sell):
#                 long_limit_sell(asset, float(position['qty']), 
#                                 float(position['current_price']) * 1.01, 
#                                 isExtHour=True) # 1% above current price
#                 print(f"\033[93m  ✓ [REPORT] {asset} additional sell order placed.\033[0m")
#             else:
#                 long_limit_buy(asset, float(position['qty']) * 2, 
#                                min(float(position['avg_entry_price']), float(position['current_price']) * 0.97), 
#                                isExtHour=True) # 3% below current price
#                 print(f"\033[92m  ✓ [REPORT] {asset} additional buy order placed.\033[0m")
#     if (not is_found):
#         price = get_price(asset)
#         quantity = 1
#         if (price is not None):
#             long_limit_buy(asset, quantity, price * 0.99, isExtHour=True)
#         print(f"\033[92m  ✓ [REPORT] {asset} is not in position, placed a buy order.\033[0m")
#         print(f"    → qty = {quantity}, ")
#         print(f"      price = {price}, ")
#         print(f"      target_price = {price * 0.99}, ")

# def buy_operation():
#     manual_buy("TNA")
#     manual_buy("CONY")


 


def main():
    fetch()
    load_nonfract_assets_info()
    print(f"Hi {TRADING_USERNAME}, Alpaca Tradebot started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if (get_cash_equity_ratio() > 0.70): manual_stockup_init(HIGH_DIVIDEND_ASSETS)
    manual_stockup_init(INDICES)


    # from .schedular import main as schedular_start
    # schedular_start()

    # report()


    # cancel_order_by_asset('ASTS', "alpaca_data2/orders.csv")	
    # cancel_all_orders_in("alpaca_data2/orders.csv")
    # long_limit_sell("AA", 10, 65.70, isExtHour=True)
    
    # long_limit_sell("ASTS", 2, 106.02, isExtHour=True) # for me
    # long_limit_sell("SLV", 9.56, 70.00, isExtHour=True) # for me
    # long_limit_buy("ASTS", 2.00, 99.00, isExtHour=True)
    # long_limit_buy("MRK", 4, 119, isExtHour=True)


    rows=fetch()
    # liquidate(rows, 1.005, INDICES) # LIQUIDATE: release all long positions

    # cancel_all_orders_in("alpaca_data2/orders.csv")
    # short_operation(is_checking=False, is_double_scaled=False) # double scale for 12%, normal for 6%
    short_operation(is_checking=True)


    
    # modern_logic()

    # short_finishing()

    # load_weeklytrades_activity()




    # index_logic()

    # logic()
    
    # report()






    # # ################# STOCK UP - REBALANCE
    # # cancel_all_orders_in("alpaca_data2/orders.csv")
    # rows=fetch()
    # rebalance(rows, pct_discount=1.99, target_pnl=-13.0, is_bullish=True, bound=200.0)    # Bullish market
    # # rebalance(rows, pct_discount=1.99, target_pnl=-6.0, is_bullish=False)    # Bearish market



    # # ################# MANUAL BUY / SELL
    # ######### MANUAL SHORTING (SELL->BUY, combined)
    # short_assets_amounts = [
    #     ("RGTI", 500),
    #     ("JOBY", 500),
    #     ("OKLO", 500),
    #     ("QBTS", 500),
    #     ("RMBS", 500),
    # ]
    # for asset, dollar_amount in short_assets_amounts:
    #     price = get_price(asset)
    #     if (price is not None):
    #         quantity = dollar_amount / price
    #         short_sell(asset, quantity, price)



    # ######### MANUAL BUY
    # long_limit_buy("TSLL", 5.00, 19.00, isExtHour=True)
    # long_limit_buy("TSLZ", 5.00, 0.75, isExtHour=True)
    # long_limit_buy("CONI", 0.01, 32.10, isExtHour=True)
    # long_limit_buy("SBUX", 0.01, 32.10, isExtHour=True)
    # long_limit_buy("RGTI", 30.00, 43.50, isExtHour=True)

    # ######### MANUAL SELL
    # long_limit_sell("RGTI", 30.00, 47.50, isExtHour=True)
    # 
    # long_limit_sell("RGTI", 45.00, 45.00, isExtHour=True)
    # long_limit_sell("RGTI", 30.00, 44.60, isExtHour=True)
    # long_limit_sell("OSCR", 1.84, 19.15, isExtHour=True)
    # long_limit_sell("MU", 0.21, 163.72, isExtHour=True)
    # long_limit_sell("WDAY", 0.13, 247.69, isExtHour=True)
    # long_limit_sell("ASML", 0.03, 962.61, isExtHour=True)
    # long_limit_sell("NVOX", 20, 3.60, isExtHour=True)
    # long_limit_sell("NBIS", 100.01, 97.00, isExtHour=True) #NBIS restock needed
    # long_limit_sell("INTW", 1, 20.12, isExtHour=True)












    # # Run report for yesterday
    # yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    # load_trades_activity(Path(f"reports/{yesterday}-trades.xlsx"), yesterday)





def manual_stockup_init(needed=None):
    ################# STOCKUP - ENTRY BUY (or Micro buy)
    if needed is None:
        needed=[
            # tech
            "ADP",
            "COIN",
            "TSLA",
            "MSTR",
            "HOOD",
            "MARA",
            "NVDA",
            "TSM",
            "SMCI",
            "AI",
            "GOOGL",
            "CVNA",
            "NFLX",
            "RDDT",
            "MRNA",
            "PLTR",
            "GDX",
            "AMZN",
            "AMD",
            "XYZ",
            "META",
            "SNOW",
            "AAPL",
            "ABNB",
            "PYPL",
            "MSFT",
            "XOM",
            "DIS",
            "RKLB",
            "ETH",
            
            # "BITQ", # general crypto 1
            # "LMBO", # general crypto 2

            # "STRC", # crypto mining
            # "MSTR",
            # "STRF",
            # "STRK",

            # financial
            "JPM", # JPMorgan Chase
            "BAC", # Bank of America
            "WFC", # Wells Fargo
            "MS", # Morgan Stanley
            "GS", # Goldman Sachs
            "C", # Citigroup
            "SCHW", # Charles Schwab
            "COF", # Capital One Financial
            "PNC", # PNC Financial Services
            "BK", # BNY Mellon (Bank of New York Mellon)
            "USB", # U.S. Bancorp

            # healthcare
            "ABBV",
            "AMGN",

            # ETC
            "AZN",
            "STLA",
            "PSO",
            "ORCL",
            "MDT",
            "TSM",
            "CBRL",


            # industrial
            "HD",
            "CVX",
            "SMR",
            "SBUX",
            "NKE",
            "AEO",
            "LOW",
            "DUK",

            # automotive
            "HMC",
            "TM",
            "F",
            "GM",



            # energy / materials
            "USAR",
            "UUUU",
            "LEU",
            "MP",
            "UEC",
            "OKLO",
            "NNE",
            "SMR",
        ]
        
    if not isinstance(needed, list) or len(needed) == 0:
        print("No assets provided for manual stockup.")
        return
    
    needed=set(needed)
    print("\n=== MANUAL STOCKUP INIT LOGIC ===")
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    positions = resp.json()
    current_symbols = {p["symbol"] for p in positions if float(p.get("qty", 0)) > 0}
    for ticker in needed:
        cancel_order_by_asset(ticker, "alpaca_data2/orders.csv")
        time.sleep(0.2)
        price = get_price(ticker)
        quantity = math.ceil(100 / price) / 100
        if(quantity < 0.01): quantity = 0.01
        if (ticker not in current_symbols):
            long_limit_buy(ticker, quantity, price * 0.985, isExtHour=True)
            print(f"Hi {ticker}@{price} qty={quantity}")


