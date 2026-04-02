# Stock Analysis & Regression Tool

A Python-based financial tool designed to screen the market for specific trading conditions and automatically generate detailed 1-year historical regression and volatility visualizations.

## Features

*   **Dual Strategies:**
    *   **Shorting Pipeline:** Scans for high-flying day gainers ($1B+ Market Cap, >10% gain, >=$10 price) that might be overextended.
    *   **Longing Pipeline:** Scans for heavily beaten-down mega caps ($100B+ Market Cap, < -7% drop, >=$10 price) looking for bounce opportunities.
*   **Automated Screening:** Integrates with Yahoo Finance screeners to find candidates dynamically while filtering out stocks nearing their ex-dividend dates.
*   **Advanced Visualizations:** For each candidate, the tool automatically generates three distinct charts:
    1.  `{ticker}.png`: A 1-year daily close chart overlaid with a linear regression trendline and $R^2$ stats.
    2.  `{ticker}_pct_ordinary.png`: A graph showing the percentage deviation of the actual price from the theoretical regression line.
    3.  `{ticker}_pct_derivative.png`: A volatility chart plotting daily percentage changes, including Mean Absolute Deviation (MAD) and Standard Deviation (SD).
*   **Modular Architecture:** Clean, highly cohesive codebase utilizing Dependency Injection, Facade, Strategy, and Template Method design patterns for easy extension.

## Directory Structure

*   `main.py`: The main orchestrator where all strategy constraints and configurations are defined.
*   `stock_analysis/`: The core package containing the data processing logic.
    *   `screener.py`: Handles API requests and applies filtering logic.
    *   `data_fetcher.py`: A Facade over `yfinance` to retrieve historical market data.
    *   `plotter.py`: Generates and saves the matplotlib visualizations.

## How to Run

1. Ensure you have the required dependencies installed (`yfinance`, `pandas`, `matplotlib`, `numpy`, `scipy`, `requests`).
2. Run the main script:
   ```bash
   python main.py
   ```
3. The tool will print a summary to the console and save the generated graphs to the `./shorting_data/` and `./longing_data/` directories.
