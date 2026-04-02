# Data Sourcing Architecture & TODOs

This document outlines the strategic plan for integrating multiple financial APIs into the trading bot. To ensure resilience, performance, and cost-effectiveness, the bot will employ a layered data-sourcing architecture.

## 1. Alpaca API (Primary Real-Time & Execution)
Alpaca will serve as the core broker integration and real-time data engine.
*   **Account Management:** Fetching personal portfolio balances, purchasing power, and position tracking.
*   **Order Execution:** Submitting, modifying, and canceling market, limit, stop, and trailing stop orders.
*   **Real-time Market Data:** Utilizing Alpaca's WebSockets for live tick-by-tick or minute-by-minute OHLCV data to trigger immediate trading signals.
*   **Paper Trading:** Safely testing algorithmic strategies in a simulated environment before deploying capital.

## 2. Yahoo Finance (`yfinance`) (Primary Historical & Metadata)
Yahoo Finance remains the workhorse for heavy, non-real-time data analysis. Because it is free and unrestricted, it should be queried first for any historical backtesting or deep analysis.
*   **Deep Historical Data:** Fetching multi-year daily/weekly OHLCV data for linear regressions and volatility metrics (MAD/SD calculations).
*   **Company Metadata:** Retrieving static or slowly changing data such as Sector, Industry, Business Summaries, and employee counts.
*   **Basic Fundamentals:** Pulling recent income statements, balance sheets, and cash flow data (limited to ~4 years).
*   **Corporate Actions:** Tracking dividends, stock splits, and upcoming earnings calendar dates.

## 3. Financial Modeling Prep (FMP) (Fallback & Specialized Data)
FMP will act as a robust safety net and a source for advanced fundamental metrics. To conserve API limits on the free/lower-tier plans, FMP should strictly be queried **once per day** or only when `yfinance` fails.
*   **High-Reliability Fallback:** If `yfinance` throttling or scraping errors occur during historical data fetching, the system should catch the exception and fall back to FMP's REST API.
*   **Advanced Pre-calculated Metrics:** Fetching complex financial ratios (P/E, P/B, ROE, DCF, Enterprise Value) without needing to manually calculate them from raw `yfinance` balance sheets.
*   **Deep Financial History:** Accessing decades of fundamental data (10-K/10-Q filings) if a long-term value investing strategy is implemented.
*   **Alternative Data (Alpha Generation):** 
    *   Insider trading logs (tracking CEO/CFO buys/sells).
    *   Institutional fund holdings (13F filings).
    *   Sentiment analysis and market news aggregation.
    *   Senate/Congressional trading records.
*   **Advanced Screening:** Replacing the brittle Yahoo predefined screener URLs (`day_gainers`, `day_losers`) with programmatic FMP screener API calls for precise, multi-conditional filtering.

---

## Actionable TODOs

### Phase 1: Alpaca Integration
- [ ] Install the `alpaca-py` SDK.
- [ ] Create an `AlpacaService` inside the `services/` layer to handle API authentication (Paper Trading keys).
- [ ] Implement account balance polling and basic order execution (Market/Limit buys).
- [ ] Transition real-time price checks from `yfinance` to Alpaca.

### Phase 2: FMP Fallback System
- [ ] Register for an FMP API key and store it securely in a `.env` file.
- [ ] Create an `FMPService` within the `services/` layer.
- [ ] Implement a **Fallback/Retry Pattern** in `services/fetcher.py`: Attempt `yfinance.download()`, and if it throws an exception or returns empty, automatically route the request to `FMPService`.
- [ ] Refactor `services/screener.py` to query the FMP Screener endpoint instead of scraping Yahoo's predefined URLs, ensuring more stable and customizable daily candidate generation.

### Phase 3: Advanced Strategy Implementation
- [ ] Once a day, run a batch job using FMP to pull and cache advanced alternative data (e.g., Insider Trading, Sentiment) for the stocks that passed the initial screener.
- [ ] Integrate these new fundamental/alternative metrics into the `TickerRuntimeData` DTO to allow the orchestrator to make more sophisticated Go/No-Go trading decisions.