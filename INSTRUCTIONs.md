# Session Instructions & Development Style

This document records the architectural decisions, design patterns, and coding style established in this session to ensure consistency in future sessions.

## 1. Architectural Principles
*   **Modular Architecture (Domain-Driven):** The application is strictly separated into logical packages:
    *   `alphavi/`: Core domain package containing high-level logic, data models, and sub-packages.
    *   `alphavi_util/`: General utility package (e.g., environment variable retrieval) that is independent of the business domain and can be published separately.
    *   `alphavi/ftp/`: Sub-package specifically for handling external API integrations (Financial Modeling Prep).
    *   `alphavi/alpaca/`: Sub-package specifically for handling broker API integrations (Alpaca).
*   **Single Responsibility per File:** 
    *   `models.py`: Data structures (`StockDataDTO`, `StockDataTable`, `ActiveOrderDTO`, `ActiveOrderTable`, `AccountDTO`).
    *   `endpoints.py`: High-level functional orchestrators (`load_market_data`, `patch_market_data`).
    *   `fmp_service.py`: Low-level HTTP requests and JSON parsing for a single service.
*   **Functional Endpoints over Abstract Controllers:** Keep the orchestration layer simple and direct by using functional endpoints rather than overly abstract or unnecessary controller classes (`MarketDataService` was explicitly removed in favor of functions).
*   **Smart Imports (Facade Pattern at Module Level):** Use `__init__.py` files to expose public interfaces (classes, functions, models) for clean, top-level imports. This hides the internal file structure from the end user (e.g., `from alphavi import load_market_data`).
*   **Entry Point Wrapper:** The application is executed via a lightweight wrapper `main.py` located at the root, which delegates to the package's internal `__main__.py` or endpoints.
*   **Strategic Caching vs. Real-Time Data:** Static or slow-changing data (e.g., available assets) should be cached in memory (Singleton properties) after the first fetch to minimize API load. Dynamic data (e.g., positions, open orders, account info) MUST be fetched in real-time without caching to ensure data accuracy.

*   **API Efficiency & Condensed DTOs:** Fetch only the strictly necessary endpoints to minimize network overhead and API cost. Map these to condensed DTOs containing only the actionable fields needed for the domain.
*   **Client-Side Computation:** Prefer computing metrics (e.g., RSI, moving averages) locally using raw historical data whenever the specific pre-computed metric endpoints are restricted or require additional API calls.
*   **Debug & Audit Logging:** Implement optional `debug` flags in API Singleton services. When enabled, raw HTTP JSON responses should be written to designated, locally defined directories (e.g., `log_alpaca`, `log_ftp`) for auditing and inspection without polluting standard output.

## 2. Design Patterns Utilized
When implementing logic, explicitly mention standard software design patterns using **inline comments**, labeling sequential steps if applicable. Do **NOT** put design pattern explanations inside formal docstrings.

*   **Singleton Pattern:** Used for external API services (e.g., `FMPService`, `AlpacaService`) to ensure only one instance of the HTTP client and API configuration exists throughout the application lifecycle.
    *   *Documentation:* Use sequential inline comments tracking the lifecycle: `# [Singleton] (1): ...` for allocation, `# [Singleton] (2): ...` for initialization, and `# [Singleton] (3): ...` for invocation.
*   **Data Transfer Object (DTO):** Used to encapsulate and pass a comprehensive set of runtime data metrics for a single entity (e.g., `StockDataDTO`).
*   **Table / Registry Pattern:** Used as a logical abstraction over basic data structures (like dictionaries) to hold a collection of unique DTOs safely (e.g., `StockDataTable` enforcing unique ticker symbols).
    *   *Documentation:* Use sequential inline comments tracking the lifecycle: `# [Registry] (1): ...` for initialization of the store, `# [Registry] (2): ...` for adding/registering, and `# [Registry] (3): ...` for retrieval.
*   **Facade Pattern (Smart Imports):** Exposing deep module members at the package root via `__init__.py` to provide a unified, clean interface to the package.
    *   *Documentation:* Use sequential inline comments tracking the structural usage: `# [Facade] (1): ...` when exposing internal modules inside `__init__.py` files, and `# [Facade] (2): ...` when consuming the exposed interface elsewhere.
*   **Aggregator Pattern:** Used to efficiently combine data from multiple independent API endpoints (e.g., fetching positions and assets) into a single, cohesive data structure (e.g., `StockDataTable`) while avoiding nested loops to ensure optimal runtime complexity (e.g., O(n+m)).
    *   *Documentation:* Use sequential inline comments tracking the aggregation steps: `# [Aggregator] (1): ...` for fetching and populating the base data, and `# [Aggregator] (2): ...` for fetching and merging subsequent data streams into the structure.

## 3. Coding & Documentation Style
*   **Docstrings:** All modules, classes, and functions **MUST** have standard Python docstrings briefly explaining their purpose, arguments (`Args:`), and return values (`Returns:`).
*   **Inline Comments:** Use clear, concise inline comments. For design patterns, use the `# [PatternName] ([sequentialStepNumber]): [comment/explain]` format immediately preceding the relevant code block. (e.g., `# [Singleton] (1): Allocate instance` in `__new__`, `# [Singleton] (2): Initialize state` in `__init__`, and `# [Singleton] (3): Invoke instance` where used).
*   **Data Integrity:** **ALWAYS** validate and sanitize data before operations. This includes checking if lists/strings are empty or None, and validating object types before mutating state or making external requests. Do not use sequential step numbers for basic data integrity checks.
*   **Robust Environment Retrieval:** Use utilities that gracefully fall back across OS environment variables, PyInstaller temporary directories (`sys._MEIPASS`), and current working directory `.env` files.
*   **Always resolve warnings:** Address any warnings generated by Python packages appropriately using idiomatic features.