# Stock Analysis & Regression Tool

A Python-based financial tool designed to screen the market for specific trading conditions, calculate statistical deviations, and automatically generate detailed 1-year historical regression and volatility visualizations.

## Features

*   **Dual Strategies:**
    *   **Shorting Pipeline:** Scans for high-flying day gainers (>$1B Market Cap, >10% gain, >=$10 price) that might be overextended.
    *   **Longing Pipeline:** Scans for heavily beaten-down mega caps (>$100B Market Cap, < -4.5% drop, >=$10 price) looking for bounce opportunities.
*   **Automated Screening:** Integrates with Yahoo Finance screeners to find candidates dynamically while filtering out stocks nearing their ex-dividend dates.
*   **Advanced Visualizations:** For each candidate, the tool automatically calculates metrics and generates three distinct charts:
    1.  `{ticker}.png`: A 1-year daily close chart overlaid with a linear regression trendline and $R^2$ stats.
    2.  `{ticker}_pct_ordinary.png`: A graph showing the percentage deviation of the actual price from the theoretical regression line. Truncated from the first zero-crossing point to highlight recent relevant deviation, displaying the total number of zero-crossings.
    3.  `{ticker}_pct_derivative.png`: A volatility chart plotting daily percentage changes, including horizontal lines for Mean Absolute Deviation (MAD) and Standard Deviation (SD).
*   **Rich Terminal Output:** Uses the `rich` library to render a clean, colored summary table of all processed candidates, including their sector, metrics, and price changes.
*   **Domain-Driven Architecture:** Clean, highly cohesive codebase utilizing Layered Architecture and explicit design patterns (Facade, DTO, Registry, Template Method) for easy extension.

## Directory Structure

*   `app.py`: The Controller / Orchestrator. Defines strategies, coordinates fetching, analysis, and presentation.
*   `core/`: Domain models and internal state.
    *   `models.py`: Contains DTOs (`TickerRuntimeData`) and registries (`AnalysisSession`).
*   `services/`: External API integrations and business logic.
    *   `screener.py`: Handles API requests to Yahoo screeners.
    *   `fetcher.py`: Facade over `yfinance` to retrieve historical market data and company metadata (Sector).
    *   `analyzer.py`: Core mathematical and statistical logic (SciPy, Pandas).
*   `views/`: Presentation layer.
    *   `plotter.py`: Generates and saves matplotlib visualizations.
    *   `cli.py`: Renders the `rich` summary table to the terminal.
*   `_data/`: Output directory where generated graphs are stored (e.g., `_data/shorting`, `_data/longing`).

## How to Run

1. Ensure you have the required dependencies installed:
   ```bash
   pip install yfinance pandas matplotlib numpy scipy requests rich
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. The tool will print a rich summary table to the console and save the generated graphs to the `_data/shorting/` and `_data/longing/` directories.