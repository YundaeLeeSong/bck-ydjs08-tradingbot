import os
import json
import csv
from dotenv import load_dotenv
import time
import requests
from datetime import datetime
from typing import Optional, List


from pvm import get_resource
from pathlib import Path




# ─── Load env & headers ────────────────────────────────────────────────────────
load_dotenv(get_resource(".env"))
BASE_URL   = os.getenv("APCA_API_BASE_URL")
API_KEY    = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")

if not (API_KEY and API_SECRET):
    BASE_URL="https://paper-api.alpaca.markets"
    API_KEY="PKD7M8VMC1D6YOQ6CW57"
    API_SECRET="4Euz3jubAEwIvboqeWcJRkbuROGqCFNJ7OzNPLUe"

if not BASE_URL.startswith("https://"):
    raise RuntimeError(f"Invalid BASE_URL: {BASE_URL}/v2")

HEADERS = {
    "APCA-API-KEY-ID":     API_KEY,
    "APCA-API-SECRET-KEY": API_SECRET,
}









def cancel_order(order_id): # DELETE
    """
    Cancels an existing order by ID.
    Returns:
      - The JSON order object if the server returns one,
      - An empty dict if the server returns 204 No Content.
    """
    url = f"{BASE_URL}/v2/orders/{order_id}"
    resp = requests.delete(url, headers=HEADERS)
    resp.raise_for_status()
    # If there's no JSON body, return an empty dict
    # "204 No Content", which means the server successfully processed 
    # the request but is not returning any content.
    if resp.status_code == 204 or not resp.text: 
        print("Canceled order object:", order_id)
        return {}
    return resp.json()















# ─── Fetch & save open orders ──────────────────────────────────────────────────
def fetch_orders(save_path="alpaca_data/orders.json"):
    """
    Fetches all open orders and writes them to `save_path`.
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    url = f"{BASE_URL}/v2/orders"
    params = {
        "status": "open",     # only open orders
        "limit": 500,         # max per page (optional) [5,10,20,50(default),100,500]
        # you can add: after, until, direction, nested, etc.
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()







def load_orders(path = "alpaca_data/orders.json"):
    print(f"---- Loading latest orders from Alpaca API... at {path} ----")
    ### [GET] Fetch orders by assets
    path = Path(path)
    csv_path = path.with_suffix('.csv')
    orders = fetch_orders(path)             # your existing function
    with open(path, "w") as f: json.dump(orders, f, indent=2)
    print(f"✔ (loading...) Saved {len(orders)} open orders to {path}")
    # if you need to inspect them in code:
    for o in orders:
        print(f"- {o['id']} | {o.get("status")} | {o['symbol']} | {o['type']}_{o['side']} {o.get('qty') or o.get('notional')}@{o['limit_price'] or o['stop_price']}")
    save_orders_to_csv(orders, csv_path)               # writes alpaca_data/orders.csv




def save_orders_to_csv(orders, filename="alpaca_data/orders.csv"):
    """
    Given `orders` (a list of order dicts), write out a CSV with columns:
      id, asset (symbol), side, qty, price (limit_price)
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fieldnames = ["id", "asset", "type", "side", "qty", "price","status"]
    with open(get_resource(filename,isDebug=True), "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for o in orders:
            writer.writerow({
                "id":    o.get("id"),
                "asset": o.get("symbol"),
                "type":  o.get("type"),
                "side":  o.get("side"),
                "qty":   o.get("qty") or o.get("notional") or "",
                "price": o.get("limit_price") or o.get("stop_price"),
                "status": o.get("status") or "",
            })
    print(f"✔ Saved {len(orders)} orders to {filename}\n\n")









# example CSV format (alpaca_data/orders.csv):
# id,asset,side,qty,price,status
# 180f4e45-d08e-440b-add6-04e916063527,NVDA,buy,4,124.4,accepted
# 7baf67ce-d553-44de-91a4-75af3a28cf6d,NVDA,buy,2,126.24,accepted
# 82b6b1c2-8c8d-4755-bae6-8e732329b476,NVDA,buy,1,127.65,accepted
# 55ac9e30-35ce-4ce9-8cc1-148c2baf8c5d,INTC,buy,32,19,accepted




def cancel_all_orders_in(
    csv_path: str = "alpaca_data/orders.csv",
    exceptions: Optional[List[str]] = None
) -> None:
    """
    Reads a CSV with an 'id' column, cancels each order by that ID,
    and rewrites the CSV file without the successfully canceled rows.
    """
    load_orders(csv_path)
    temp_rows = []
    # Read all rows first
    with open(get_resource(csv_path,isDebug=True), newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            order_id = row.get("id")
            # if not order_id:
            #     # keep rows without an 'id'
            #     temp_rows.append(row)
            #     continue
            try:
                cancel_resp = cancel_order(order_id)
                print(f"✅ Canceled {order_id}")
                print(cancel_resp)
                time.sleep(0.5)
                # On success, we do NOT append row → it's removed
            except Exception as e:
                if (order_id is None): continue
                print(f"❌ Failed to cancel {order_id}: {e}")
                # keep this row for retries later
                temp_rows.append(row)
                continue

    # Rewrite CSV with only remaining rows
    # (rows that failed or had no id)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(get_resource(csv_path,isDebug=True), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(temp_rows)
    print(f"✔ CSV updated, {len(temp_rows)} rows remain in {csv_path}")






def cancel_order_by_asset(
    asset_symbol: str,
    csv_path: str = "alpaca_data/orders.csv",
    exceptions: Optional[List[str]] = None
) -> None:
    """
    Cancels all open orders for a given asset symbol (e.g., "NVDA") found in the CSV,
    except for assets listed in `exceptions`.
    Removes successfully canceled orders from the CSV.
    """
    # load_orders(csv_path)      ### do not want to load every single time in a loop
    if exceptions is not None and asset_symbol in exceptions: 
        print(f"✅⏭✅⏭✅⏭ Skipping canceling the order of {asset_symbol} (in exceptions)")
        return
    temp_rows = []
    canceled_count = 0
    with open(get_resource(csv_path, isDebug=True), newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("asset") == asset_symbol:
                order_id = row.get("id")
                try:
                    cancel_resp = cancel_order(order_id)
                    time.sleep(0.5)
                    print(f"✅ Canceled {order_id} for {asset_symbol}")
                    canceled_count += 1
                    # Do not append, remove from CSV
                except Exception as e:
                    print(f"❌ Failed to cancel {order_id}: {e}")
                    temp_rows.append(row)
            else:
                temp_rows.append(row)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(get_resource(csv_path, isDebug=True), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(temp_rows)
    print(f"✔ Canceled {canceled_count} orders for {asset_symbol}. {len(temp_rows)} rows remain in {csv_path}")






# ─── Example usage ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    order_id = "410ef1f9-dfba-437d-8546-56387f92e6b6"
    cancel_order(order_id)





    load_orders("alpaca_data/orders.json")  # Fetches and saves open orders to JSON & CSV







    cancel_all_orders_in("alpaca_data/orders.csv")



    cancel_order_by_asset("AAPL", "alpaca_data/orders.csv")
