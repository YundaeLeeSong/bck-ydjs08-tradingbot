"""
Plotter Module
==============
Generates and saves various analytical plots.
"""
import os
import matplotlib.pyplot as plt

def _ensure_dir(dir_name):
    """Ensures the output directory exists."""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

def plot_base_regression(symbol, df, y, line, r_squared, slope, std_err, output_dir):
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

def plot_pct_ordinary(symbol, valid_index, pct_diff, num_zeros, output_dir):
    """
    Generates a plot showing the percentage deviation of actual price from the regression line.
    """
    plt.figure(figsize=(10, 5))
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
    
    plt.savefig(os.path.join(output_dir, f"{symbol}_pct_ordinary.png"))
    plt.close()

def plot_pct_derivative(symbol, daily_pct_change, mad, sd, output_dir):
    """
    Generates a plot showing daily percentage change (derivative),
    along with Mean Absolute Deviation (MAD) and Standard Deviation (SD).
    """
    plt.figure(figsize=(10, 5))
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
    
    plt.savefig(os.path.join(output_dir, f"{symbol}_pct_derivative.png"))
    plt.close()

def generate_all_plots(symbol, df, metrics, output_dir="_data/shorting"):
    """
    Delegates to specific plotting functions to generate different analytical views.
    
    Args:
        symbol (str): The stock ticker symbol.
        df (pandas.DataFrame): The historical data.
        metrics (dict): The dictionary of pre-calculated metrics.
        output_dir (str): Directory where the plots will be saved.
    """
    if df is None or df.empty or metrics is None:
        return

    _ensure_dir(output_dir)

    # [Template Method Pattern]: We define the skeleton of plotting operations here.
    plot_base_regression(
        symbol, df, metrics['y'], metrics['line'], metrics['r_squared'], 
        metrics['slope'], metrics['std_err'], output_dir
    )
    
    if len(metrics['pct_diff']) > 0:
        plot_pct_ordinary(
            symbol, metrics['valid_index'], metrics['pct_diff'], 
            metrics['num_zeros'], output_dir
        )
        
    plot_pct_derivative(
        symbol, metrics['daily_pct_change'], metrics['mad'], metrics['sd'], output_dir
    )
