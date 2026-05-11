"""
Plotter Module
==============
Generates and saves various analytical plots.
"""
import os
import matplotlib.pyplot as plt

_DEBUG_LOG_ = "log_graphs"

def _ensure_dir(dir_name):
    """Ensures the output directory exists."""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

def plot_base_regression(symbol, df, metrics):
    """
    Generates the base linear regression plot with SMA overlays and returns the figure.
    """
    fig = plt.figure(figsize=(10, 5))
    plt.plot(df.index, metrics['y'], label='Daily Close', color='#1f77b4', alpha=0.6)
    plt.plot(df.index, metrics['line'], label='1Y Trendline', color='red', linestyle='--')
    
    # Overlay SMAs
    plt.plot(df.index, metrics['priceAvg50'], label='SMA 50', color='orange', alpha=0.8, linewidth=1.2)
    plt.plot(df.index, metrics['priceAvg200'], label='SMA 200', color='purple', alpha=0.8, linewidth=1.2)
    
    plt.title(f"{symbol} 1Y Regression | R-Squared: {metrics['r_squared']:.4f}")
    plt.ylabel("Price (USD)")
    plt.grid(True, linestyle=':', alpha=0.6)
    
    # Get latest values for the text box
    current_rsi = metrics['rsi14'].iloc[-1] if not metrics['rsi14'].empty else 0.0
    
    # Error and Stats overlay
    stats_box = (f"Slope: {metrics['slope']:.4f}\n"
                 f"Std Error: {metrics['std_err']:.4f}\n"
                 f"R^2: {metrics['r_squared']:.4f}\n"
                 f"RSI (14): {current_rsi:.2f}")
    plt.gca().text(0.02, 0.95, stats_box, transform=plt.gca().transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    plt.legend()
    return fig

def plot_pct_ordinary(symbol, valid_index, pct_diff, num_zeros):
    """
    Generates a plot showing the percentage deviation from the regression line and returns the figure.
    """
    fig = plt.figure(figsize=(10, 5))
    plt.plot(valid_index, pct_diff, label='% Diff from Trend', color='purple', alpha=0.7)
    plt.axhline(0, color='red', linestyle='--')
    
    plt.title(f"{symbol} 1Y % Deviation from Regression (Zeros: {num_zeros})")
    plt.ylabel("Deviation (%)")
    plt.grid(True, linestyle=':', alpha=0.6)
    
    # Stats overlay
    stats_box = (f"Zero Crossings: {num_zeros}")
    plt.gca().text(0.02, 0.95, stats_box, transform=plt.gca().transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.legend()
    return fig

def plot_pct_derivative(symbol, daily_pct_change, mad, sd):
    """
    Generates a plot showing daily percentage change (derivative) and returns the figure.
    """
    fig = plt.figure(figsize=(10, 5))
    plt.plot(daily_pct_change.index, daily_pct_change, label='Daily % Change', color='orange', alpha=0.7)
    plt.axhline(0, color='black', linewidth=0.8)
    
    # MAD Lines
    plt.axhline(mad, color='green', linestyle='--', alpha=0.5, label='+MAD')
    plt.axhline(-mad, color='green', linestyle='--', alpha=0.5, label='-MAD')
    
    plt.title(f"{symbol} 1Y Daily % Change Volatility")
    plt.ylabel("Daily % Change")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    # Stats overlay
    stats_box = (f"MAD: {mad:.2f}%\n"
                 f"SD: {sd:.2f}%")
    plt.gca().text(0.02, 0.95, stats_box, transform=plt.gca().transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return fig

def generate_all_plots(symbol, df, metrics):
    """
    Delegates to specific plotting functions to generate different analytical views and returns them.
    
    Args:
        symbol (str): The stock ticker symbol.
        df (pandas.DataFrame): The historical data.
        metrics (dict): The dictionary of pre-calculated metrics.
        
    Returns:
        dict: A dictionary containing the generated matplotlib figure objects.
    """
    if df is None or df.empty or metrics is None:
        return {}

    plots = {}
    # [Template Method Pattern]: We define the skeleton of plotting operations here.
    plots['base_regression'] = plot_base_regression(symbol, df, metrics)
    
    if len(metrics['pct_diff']) > 0:
        plots['pct_ordinary'] = plot_pct_ordinary(
            symbol, metrics['valid_index'], metrics['pct_diff'], 
            metrics['num_zeros']
        )
        
    plots['pct_derivative'] = plot_pct_derivative(
        symbol, metrics['daily_pct_change'], metrics['mad'], metrics['sd']
    )
    
    return plots