# Session Instructions & Development Style

This document records the architectural decisions, design patterns, and coding style established in this session to ensure consistency in future sessions.

## 1. Architectural Principles
*   **Layered Architecture (Domain-Driven):** The application is strictly separated by responsibilities:
    *   `services/`: Handles external APIs and core business/math logic (`market_data_api.py`, `yahoo_finance_api.py`, `analysis.py`).
    *   `core/`: Contains pure data structures and domain models (`stock_metrics.py`, `analysis_report.py`).
    *   `views/`: Strictly responsible for presentation and rendering (`visualization.py`, `console.py`).
*   **Single Responsibility per File:** Each file must strictly hold either a single class or a collection of related functions/package-scoped variables. Do not mix multiple classes or mixed paradigms within a single file.
*   **High Cohesion & Low Coupling:** The core orchestrator (`core/__main__.py`) acts as the Controller. All business rules, constraints, and configuration MUST be explicitly defined here and passed down. Sub-modules should never contain hardcoded business logic or fixed paths. The application is executed via a lightweight wrapper (`app.py`).
*   **Modularization:** Code must be organized into logical packages following standard Python community conventions. Use an `__init__.py` to expose only the necessary public interfaces from internal modules.

## 2. Design Patterns Utilized
When implementing logic, explicitly mention standard software design patterns using **inline comments**, labeling sequential steps with `(1)`, `(2)`, etc. Do **NOT** put design pattern explanations inside formal docstrings.

*   **Facade Pattern:** Used to wrap complex dependencies (e.g., `yfinance`, statistical math) behind a simple, unified interface in our codebase.
*   **Adapter Pattern:** Used to integrate external APIs into our standard interfaces (e.g., `YahooFinanceAPI` adapting `yfinance`).
*   **Strategy Pattern:** Used to define distinct algorithms or pipelines (e.g., "Longing" vs "Shorting" strategies) in the main orchestrator.
*   **Template Method Pattern:** Used when a process requires a specific sequence of steps (e.g., calculating regression, then drawing base plot, then drawing derivative plot).
*   **Data Transfer Object (DTO):** Used to encapsulate and pass runtime data for a single entity (e.g., `StockMetrics`).
*   **Registry / State Pattern:** Used to keep track of multiple models over the course of a pipeline run (e.g., `AnalysisReport`).
*   **Dependency Injection:** Defining strategies explicitly in the main orchestrator to reduce coupling.

## 3. Coding & Documentation Style
*   **Docstrings:** All modules, classes, and functions must have standard Python docstrings briefly explaining their purpose, arguments (`Args:`), and return values (`Returns:`).
*   **Inline Comments:** Use clear, concise inline comments. For design patterns, use the `# [PatternName] ([sequentialStepNumber]): [comment/explain]` format immediately preceding the relevant code block.
*   **Data Integrity:** Always validate and sanitize data before operations (e.g., checking if an array is empty, dropping NaNs).
*   Always resolve warnings by python packages