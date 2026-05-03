1. Add a `created_at` and `equity_last` (not sure about what this field is from API call, you check it by running `python main.py`), and `pct_equity_change` fields for account DTO, from `bumblebee/external/alpaca_service.py`, you will need to see log_alpaca to exactly see the value of the field.
2. pct_equity_change should be calculated as pct change of equity_last to equity.
3. `bumblebee/est_timer.py` should be able to offer a accessor for the user to easily input (start_day, today) it should return a list of date objects that are iterable for API calls for every day btw start_day and today. (ofc, if you can take advantage of runtime by identifying weekdays and weekends, implement the such algo.)
4. **Refactor `report` Method in `AlpacaService`**:
    *   Target: `bumblebee/external/alpaca_service.py`
    *   Goal: Extract the logic inside the `report()` method into distinct, dedicated getter methods for each data type.
    *   Create new methods (e.g., `get_transactions()`, `get_journal_entries()`, `get_interests()`, `get_fees()`, `get_dividends()`), and use date param to get daily records with maximun number of rows ("limit":100). (e.g. "date":2026-05-01)
    *   Update the `report()` method (or remove it entirely if no longer needed as a bulk writer) to utilize these new individual methods, maintaining the existing file writing behavior if debug mode is off.
    *   Ensure any related changes respect the current data structures and error handling established in `fetch_endpoint`.
5. with implementation of (3) and (4), you should be able to log report data by dates (test code should be in `alphavi/__main__.py`).