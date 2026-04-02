# TODO / Data Sourcing Analysis

## yfinance Capabilities (Free Tier)
`yfinance` is a widely used open-source library that scrapes Yahoo Finance. It provides a massive amount of data without needing API keys or payment.
*   **Historical Market Data:** OHLCV (Open, High, Low, Close, Volume) and Adjusted Close across numerous timeframes (from 1m intraday to monthly).
*   **Company Information:** Sector, Industry, Business Summary, Full Time Employees, and basic company metadata.
*   **Financial Statements:** Income Statement, Balance Sheet, and Cash Flow (both Annual and Quarterly, typically limited to the last 4 years).
*   **Options Chains:** Call and Put options data including strike prices, expiration dates, volume, and implied volatility.
*   **Institutional Holdings:** Major holders, institutional ownership percentages.
*   **Corporate Actions:** Dividends, stock splits, earnings dates.

## Financial Modeling Prep (FMP) Capabilities
FMP is a powerful REST API for financial data. The free tier has constraints (like API call limits and delayed data), but paid tiers offer robust, institutional-grade datasets.
*   **Real-time Stock Prices:** Highly accurate and fast real-time data via websockets (often limited on the free tier).
*   **Extensive Fundamental Data:** Decades of historical financial statements (much deeper history than yfinance).
*   **Financial Ratios & Metrics:** Pre-calculated ratios (P/E, P/B, ROE, DCF, Enterprise Value, etc.) saving you from doing raw calculations.
*   **Alternative Data:** Sentiment analysis, institutional fund holdings (13F filings), insider trading, senate trading records.
*   **Global Market Coverage:** Better and more structured coverage of international exchanges, forex, and cryptocurrencies.
*   **Screener API:** Powerful server-side screening endpoints. Currently, our script relies on Yahoo's predefined screener URLs which can be brittle; FMP allows custom complex screening queries.

## Next Steps
*   [ ] Consider migrating to FMP for more reliable, long-term historical financial statements if performing deep value or multi-decade analysis.
*   [ ] Evaluate FMP's real-time API if the bot needs intraday trading capabilities.
*   [ ] Refactor the current `screener.py` to use a more robust API endpoint rather than scraping Yahoo's pre-defined screener pages.