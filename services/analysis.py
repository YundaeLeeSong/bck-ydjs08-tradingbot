"""
Analyzer Module
===============
Contains the core mathematical and statistical business logic for evaluating stock data.
"""
import numpy as np
import pandas as pd
from scipy import stats

def calculate_regression_metrics(df):
    """
    Calculates linear regression metrics.
    """
    y = df['Close'].values.flatten()
    x = np.arange(len(y))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    line = slope * x + intercept
    r_squared = r_value ** 2
    return y, line, slope, std_err, r_squared

def calculate_ordinary_deviation(df, y, line):
    """
    Calculates percentage deviation from the regression line and zero crossings.
    """
    mask = line >= 10
    valid_y = y[mask]
    valid_line = line[mask]
    valid_index = df.index[mask]
    
    if len(valid_y) == 0:
        return valid_index, np.array([]), 0

    pct_diff = ((valid_y - valid_line) / valid_line) * 100

    # Calculate zero crossings
    signs = np.sign(pct_diff)
    sign_changes = np.where(signs[:-1] != signs[1:])[0] + 1
    num_zeros = len(sign_changes)

    if num_zeros > 0:
        # Keep data from the first zero crossing onwards
        first_zero_idx = sign_changes[0]
        # Include the point right before to actually see the crossing
        start_idx = max(0, first_zero_idx - 1)
        pct_diff = pct_diff[start_idx:]
        valid_index = valid_index[start_idx:]

    return valid_index, pct_diff, num_zeros

def calculate_derivative_metrics(df):
    """
    Calculates daily percentage change, MAD, and SD.
    """
    close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
    daily_pct_change = close_series.pct_change() * 100
    daily_pct_change = daily_pct_change.dropna()
    
    mad = (daily_pct_change - daily_pct_change.mean()).abs().mean()
    sd = daily_pct_change.std()
    
    return daily_pct_change, mad, sd

# [Facade Pattern]: Orchestrates all data analysis calculations to decouple math logic from plotting.
def analyze_stock_data(df):
    """
    Orchestrates all data analysis calculations to decouple math logic from plotting.
    """
    y, line, slope, std_err, r_squared = calculate_regression_metrics(df)
    valid_index, pct_diff, num_zeros = calculate_ordinary_deviation(df, y, line)
    daily_pct_change, mad, sd = calculate_derivative_metrics(df)
    
    return {
        'y': y,
        'line': line,
        'slope': slope,
        'std_err': std_err,
        'r_squared': r_squared,
        'valid_index': valid_index,
        'pct_diff': pct_diff,
        'num_zeros': num_zeros,
        'daily_pct_change': daily_pct_change,
        'mad': mad,
        'sd': sd
    }