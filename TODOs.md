# Reporting System Implementation Plan

## 1. Model Enhancements
- [ ] **Update `AccountDTO`**: Add fields for aggregated account metrics:
    - `total_fees`: Combined trading and service fees.
    - `total_jofs`: Journal of Funds / adjustments.
    - `total_deposits`: Total cash inflows from transfers.
    - `total_withdrawals`: Total cash outflows from transfers.
- [ ] **Update `StockDataDTO`**: Add fields for ticker-specific cash flows:
    - `cash_spent`: Total cost of buy activities.
    - `cash_received`: Total proceeds from sell activities.

## 2. AlpacaService Refactoring
- [ ] **`get_account_info(is_report=False, after=None, until=None)`**:
    - If `is_report`, fetch activities via `_fetch_activities(after, until)`.
    - Iterate through activities to accumulate `total_fees`, `total_jofs`, `total_deposits`, and `total_withdrawals`.
    - Map these values to the `AccountDTO`.
- [ ] **`get_positions(is_report=False, after=None, until=None)`**:
    - If `is_report`, fetch activities via `_fetch_activities(after, until)`.
    - Group trade activities (fills) by ticker.
    - Calculate `cash_spent` and `cash_received` for each ticker.
    - Map these values to the corresponding `StockDataDTO` in the `StockDataTable`.

## 3. Activity Aggregation Logic
- [ ] **Categorization**: Use `if-elif-else` block to handle different Alpaca activity types:
    - `FILL`: Track buy/sell amounts for `StockDataDTO`.
    - `FEE`: Track for `total_fees`.
    - `JNLC` / `JNLS`: Track for `total_jofs`.
    - `ACATC` / `ACATS`: Track for deposits/withdrawals.
    - *Note: Identify and handle other relevant activity types as discovered.*
