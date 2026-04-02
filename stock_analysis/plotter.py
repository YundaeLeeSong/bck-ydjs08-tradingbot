"""
Plotter Module
==============
Generates and saves various analytical plots.
"""
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

def _ensure_dir(dir_name):
    """Ensures the output directory exists."""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

def plot_base_regression(symbol, df, x, y, line, r_squared, slope, std_err, output_dir):
    """
    Generates the base linear regression plot.
    """
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, y, label='Daily Close', color='#1f77b4', alpha=0.6)
    plt.plot(df.index, line, label='1Y Trendline', color='red', linestyle='--')
    
    plt.title(f"{symbol} 1Y Regression | R-Squared: {r_squared:.4f}")
    plt.ylabel("Price (USD)")
    plt.grid(True, linestyle=':', alpha=0.6)
    
    # Error and Stats overlay
    stats_box = (f"Slope: {slope:.4f}\n"
                 f"Std Error: {std_err:.4f}\n"
                 f"R^2: {r_squared:.4f}")
    plt.gca().text(0.02, 0.95, stats_box, transform=plt.gca().transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    plt.legend()
    plt.savefig(os.path.join(output_dir, f"{symbol}.png"))
    plt.close()

def plot_pct_ordinary(symbol, df, y, line, output_dir):
    """
    Generates a plot showing the percentage deviation of actual price from the regression line.
    """
    # Exclude rows where regression line value is < 10
    mask = line >= 10
    valid_y = y[mask]
    valid_line = line[mask]
    valid_index = df.index[mask]
    
    if len(valid_y) == 0:
        return

    pct_diff = ((valid_y - valid_line) / valid_line) * 100

    plt.figure(figsize=(10, 5))
    plt.plot(valid_index, pct_diff, label='% Diff from Trend', color='purple', alpha=0.7)
    plt.axhline(0, color='red', linestyle='--')
    
    plt.title(f"{symbol} 1Y % Deviation from Regression")
    plt.ylabel("Deviation (%)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    plt.savefig(os.path.join(output_dir, f"{symbol}_pct_ordinary.png"))
    plt.close()

def plot_pct_derivative(symbol, df, output_dir):
    """
    Generates a plot showing daily percentage change (derivative),
    along with Mean Absolute Deviation (MAD) and Standard Deviation (SD).
    """
    close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
    daily_pct_change = close_series.pct_change() * 100
    
    mad = (daily_pct_change - daily_pct_change.mean()).abs().mean()
    sd = daily_pct_change.std()

    plt.figure(figsize=(10, 5))
    plt.plot(df.index, daily_pct_change, label='Daily % Change', color='orange', alpha=0.7)
    plt.axhline(0, color='black', linewidth=0.8)
    
    plt.title(f"{symbol} 1Y Daily % Change Volatility")
    plt.ylabel("Daily % Change")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    # Stats overlay
    stats_box = (f"MAD: {mad:.2f}%\n"
                 f"SD: {sd:.2f}%")
    plt.gca().text(0.02, 0.95, stats_box, transform=plt.gca().transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.savefig(os.path.join(output_dir, f"{symbol}_pct_derivative.png"))
    plt.close()

def generate_all_plots(symbol, df, output_dir="./shorting_data"):
    """
    Pattern: Template Method / Strategy (1) - We define the skeleton of plotting operations here.
    Delegates to specific plotting functions to generate different analytical views.
    
    Args:
        symbol (str): The stock ticker symbol.
        df (pandas.DataFrame): The historical data.
        output_dir (str): Directory where the plots will be saved.
    """
    if df is None or df.empty:
        return

    _ensure_dir(output_dir)

    # Prep data
    y = df['Close'].values.flatten()
    x = np.arange(len(y))

    # Statistics calculation for regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    line = slope * x + intercept
    r_squared = r_value ** 2

    # Pattern: Template Method (2) - Execute sequential steps of plot generations
    plot_base_regression(symbol, df, x, y, line, r_squared, slope, std_err, output_dir)
    plot_pct_ordinary(symbol, df, y, line, output_dir)
    plot_pct_derivative(symbol, df, output_dir)
