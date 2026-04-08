"""
Financial Modeling Prep (FMP) service module.

This module provides the FMPService class, responsible for making raw HTTP
requests to the FMP API and parsing the returned JSON data into StockDataDTOs.
"""

import os
import json
import requests
from typing import Optional, Any
from alphavi_util.core import get_env_var
from alphavi.models import StockDataDTO

_DEBUG_LOG_ = "log_ftp"

class FMPService:
    """
    Financial Modeling Prep (FMP) API Service.
    
    This class is implemented as a Singleton to ensure only one instance
    of the HTTP client/configuration exists throughout the application lifecycle.
    It provides methods to aggregate comprehensive fundamental and technical
    stock data into a unified StockDataDTO object.

    Debug mode (``self.debug``) controls disk writes: raw responses are
    saved under the ``_DEBUG_LOG_`` directory. Pass ``debug=True`` or 
    ``debug=False`` on construction; defaults to ``False``.
    The first successful initialization wins.
    """
    
    _instance = None

    def __new__(cls, api_key: Optional[str] = None, debug: bool = False):
        # [Singleton] (1): Allocate the single instance if it doesn't exist.
        if cls._instance is None:
            cls._instance = super(FMPService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, api_key: Optional[str] = None, debug: bool = False):
        # [Singleton] (2): Initialize configuration once, ignore subsequent __init__ calls.
        if self._initialized:
            return
            
        self.api_key = api_key or get_env_var("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY is not set. Ensure it is in your environment or .env file.")
        
        self.base_url = "https://financialmodelingprep.com/stable"
        self.debug = bool(debug)
        self._initialized = True

    def fetch_endpoint(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """
        Executes a GET request against the FMP API and returns the parsed JSON.
        
        Args:
            endpoint (str): The specific stable API endpoint (e.g., 'profile').
            params (Optional[dict]): Query parameters to attach to the request.
            
        Returns:
            Any: The JSON response parsed as a Python dict/list, or None on failure/restriction.
        """
        url = f"{self.base_url}/{endpoint}"
        payload = params.copy() if params else {}
        payload["apikey"] = self.api_key
        
        try:
            response = requests.get(url, params=payload)
            
            file_path = None
            if self.debug:
                os.makedirs(_DEBUG_LOG_, exist_ok=True)
                symbol = params.get("symbol", "unknown") if params else "unknown"
                safe_endpoint = endpoint.replace("/", "_")
                file_path = os.path.join(_DEBUG_LOG_, f"fmp_{symbol}_{safe_endpoint}.json")

            if response.status_code == 200:
                data = response.json()
                
                if self.debug and file_path is not None:
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=4)
                    
                return data
            elif response.status_code in [402, 403]:
                print(f"!!! RESTRICTED (HTTP {response.status_code}): {endpoint} is restricted on the current tier.")
                
                if self.debug and file_path is not None:
                    with open(file_path, "w") as f:
                        f.write(f"RESTRICTED Error {response.status_code}: {response.text}")
                
                return None
            else:
                if self.debug and file_path is not None:
                    try:
                        error_data = response.json()
                        with open(file_path, "w") as f:
                            json.dump({"error_code": response.status_code, "response": error_data}, f, indent=4)
                    except Exception:
                        with open(file_path, "w") as f:
                            f.write(f"Error {response.status_code}: {response.text}")
                
                print(f"!!! API ERROR (HTTP {response.status_code}): {response.text[:200]}")
                return None
        except Exception as e:
            print(f"!!! CRITICAL ERROR: {e}")
            return None

    def get_stock_data(self, ticker: str) -> StockDataDTO:
        """
        Aggregates data from specific FMP endpoints to construct a condensed
        StockDataDTO containing only essential metrics.
        
        Args:
            ticker (str): The stock symbol to query (e.g., 'AAPL').
            
        Returns:
            StockDataDTO: A data transfer object populated with the gathered metrics.
        """
        dto = StockDataDTO(symbol=ticker)
        print(f"Fetching aggregated data for {ticker}...")

        def get_first(data):
            # Helper to safely extract the first dict from a JSON list response
            if data and isinstance(data, list) and len(data) > 0:
                return data[0]
            return {}

        # 1. Profile
        profile_data = get_first(self.fetch_endpoint("profile", {"symbol": ticker}))
        dto.name = profile_data.get("companyName", "")
        dto.industry = profile_data.get("industry", "")
        dto.sector = profile_data.get("sector", "")
        dto.marketCap = profile_data.get("mktCap", profile_data.get("marketCap", 0.0))
        dto.beta = profile_data.get("beta", 0.0)
        dto.volume = profile_data.get("volume", profile_data.get("volAvg", 0))
        dto.averageVolume = profile_data.get("volAvg", profile_data.get("averageVolume", 0))

        # 2. Ratios
        ratios_data = get_first(self.fetch_endpoint("ratios", {"symbol": ticker}))
        dto.priceToEarningsRatio = ratios_data.get("priceToEarningsRatio", 0.0)
        dto.priceToEarningsGrowthRatio = ratios_data.get("priceToEarningsGrowthRatio", 0.0)
        dto.debtToEquityRatio = ratios_data.get("debtToEquityRatio", 0.0)
        dto.freeCashFlowOperatingCashFlowRatio = ratios_data.get("freeCashFlowOperatingCashFlowRatio", 0.0)

        # 3. Key Metrics
        metrics_data = get_first(self.fetch_endpoint("key-metrics", {"symbol": ticker}))
        dto.currentRatio = metrics_data.get("currentRatio", 0.0)
        dto.enterpriseValue = metrics_data.get("enterpriseValue", 0.0)
        dto.returnOnInvestedCapital = metrics_data.get("returnOnInvestedCapital", 0.0)
        dto.evToEBITDA = metrics_data.get("evToEBITDA", 0.0)
        dto.incomeQuality = metrics_data.get("incomeQuality", 0.0)
        dto.grahamNumber = metrics_data.get("grahamNumber", 0.0)

        # 5. Discounted Cash Flow
        dcf_data = get_first(self.fetch_endpoint("discounted-cash-flow", {"symbol": ticker}))
        dto.dcf = dcf_data.get("dcf", 0.0)

        # 6. Historical (Latest Day - Technicals)
        hist_resp = self.fetch_endpoint("historical-price-eod/full", {"symbol": ticker})
        if hist_resp and isinstance(hist_resp, dict) and "historical" in hist_resp:
            hist_list = hist_resp["historical"]
            if hist_list and len(hist_list) > 0:
                dto.vwap = hist_list[0].get("vwap", 0.0)
        elif hist_resp and isinstance(hist_resp, list) and len(hist_resp) > 0:
            dto.vwap = hist_resp[0].get("vwap", 0.0)

        # 7. Analyst Estimates
        estimates_data = get_first(self.fetch_endpoint("analyst-estimates", {"symbol": ticker, "period": "annual"}))
        dto.epsLow = estimates_data.get("estimatedEpsLow", estimates_data.get("epsLow", 0.0))
        dto.epsAvg = estimates_data.get("estimatedEpsAvg", estimates_data.get("epsAvg", 0.0))
        dto.epsHigh = estimates_data.get("estimatedEpsHigh", estimates_data.get("epsHigh", 0.0))

        return dto
