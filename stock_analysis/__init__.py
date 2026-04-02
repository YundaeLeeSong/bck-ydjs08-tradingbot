"""
Stock Analysis Package
======================
A modular package for fetching stock data, screening for specific market
conditions, and generating analytical plots.
"""
from .screener import get_filtered_movers
from .data_fetcher import fetch_historical_data
from .plotter import generate_all_plots
