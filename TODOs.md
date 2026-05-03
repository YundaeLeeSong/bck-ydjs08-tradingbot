1. **Refactor `report` Method in `AlpacaService`**:
    *   Target: `bumblebee/external/alpaca_service.py`
    *   Goal: Extract the logic inside the `report()` method into distinct, dedicated getter methods for each data type.
    *   Create new methods (e.g., `get_transactions()`, `get_journal_entries()`, `get_interests()`, `get_fees()`, `get_dividends()`).
    *   Update the `report()` method (or remove it entirely if no longer needed as a bulk writer) to utilize these new individual methods, maintaining the existing file writing behavior if debug mode is off.
    *   Ensure any related changes respect the current data structures and error handling established in `fetch_endpoint`.