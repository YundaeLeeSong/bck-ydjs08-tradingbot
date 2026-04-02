# Session Instructions & Development Style

This document records the architectural decisions, design patterns, and coding style established in this session to ensure consistency in future sessions.

## 1. Architectural Principles
*   **High Cohesion & Low Coupling:** The entry point (`main.py`) acts as the orchestrator. All business rules, constraints, and configuration (like paths, minimum price, screener IDs) MUST be explicitly defined here and passed down as arguments. Sub-modules should never contain hardcoded business logic or fixed paths.
*   **Modularization:** Code must be organized into logical packages following standard Python community conventions. Use an `__init__.py` to expose only the necessary public interfaces from internal modules.

## 2. Design Patterns Utilized
When implementing logic, explicitly mention standard software design patterns in comments, labeling sequential steps with `(1)`, `(2)`, etc.

*   **Facade Pattern:** Used to wrap complex third-party dependencies (e.g., `yfinance`) behind a simple, unified interface in our codebase. This isolates the rest of the application from external API changes.
*   **Strategy Pattern:** Used to define distinct algorithms or pipelines (e.g., "Longing" vs "Shorting" strategies) in the main orchestrator, which then delegates execution to generic functions using specific parameters.
*   **Template Method Pattern:** Used when a process requires a specific sequence of steps (e.g., calculating regression, then drawing base plot, then drawing derivative plot). The skeleton is defined in a main function, delegating specific steps to sub-functions.
*   **Iterator Pattern:** Explicitly looping over a collection of target objects (like fetched stocks) to perform operations sequentially.

## 3. Coding & Documentation Style
*   **Docstrings:** All modules, classes, and functions must have standard Python docstrings briefly explaining their purpose, arguments (`Args:`), and return values (`Returns:`).
*   **Inline Comments:** Use clear, concise inline comments. For design patterns or complex sequential logic, use the `Pattern: [Name] (Step #)` format.
*   **Data Integrity:** Always validate and sanitize data before mathematical operations (e.g., checking if an array is empty, ensuring a divisor is not zero, filtering out impossible hypothetical values like prices $< 10$).
*   **Formatting:** When displaying calculations like percentages, format them cleanly (e.g., `.2f%`) *after* all mathematical operations are complete.