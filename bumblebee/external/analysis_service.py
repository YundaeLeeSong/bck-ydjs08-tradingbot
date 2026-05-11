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
    valid_y = y
    valid_line = line
    valid_index = df.index
    
    if len(valid_y) == 0:
        return valid_index, np.array([]), 0, []

    with np.errstate(divide='ignore', invalid='ignore'):
        pct_diff = np.where(valid_line != 0, ((valid_y - valid_line) / valid_line) * 100, 0.0)

    # Calculate zero crossings
    signs = np.sign(valid_y - valid_line)
    sign_changes = np.where(signs[:-1] != signs[1:])[0] + 1
    num_zeros = len(sign_changes)

    return valid_index, pct_diff, num_zeros, sign_changes

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

def calculate_technical_indicators(df):
    """
    Calculates SMA 50, SMA 200, and RSI 14.
    """
    close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
    
    # Simple Moving Averages
    priceAvg50 = close_series.rolling(window=50, min_periods=1).mean()
    priceAvg200 = close_series.rolling(window=200, min_periods=1).mean()
    
    # RSI 14
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    
    # Avoid division by zero
    rs = np.where(loss == 0, 100, gain / loss)
    rsi14 = 100 - (100 / (1 + rs))
    rsi14_series = pd.Series(rsi14, index=df.index)
    
    return priceAvg50, priceAvg200, rsi14_series

def analyze_stock_data(df):
    """
    Orchestrates all data analysis calculations to decouple math logic from plotting.
    Iteratively normalizes timeline by deleting data before the first zero crossing 
    until the regression line and price graph start exactly at their first intercept.
    """
    # Calculate technical indicators on the FULL dataset to preserve moving average history
    priceAvg50, priceAvg200, rsi14 = calculate_technical_indicators(df)
    
    # Iteratively find the true mathematical first intercept
    max_iterations = 100
    for _ in range(max_iterations):
        y, line, slope, std_err, r_squared = calculate_regression_metrics(df)
        valid_index, pct_diff, num_zeros, sign_changes = calculate_ordinary_deviation(df, y, line)
        
        if num_zeros > 0 and len(sign_changes) > 0:
            first_zero_idx = sign_changes[0]
            # If the intercept is between index 0 and 1, the graph starts at the intercept
            if first_zero_idx <= 1 or len(df) < 30:
                break
                
            start_idx = max(0, first_zero_idx - 1)
            cut_off_date = valid_index[start_idx]
            df = df.loc[cut_off_date:].copy()
        else:
            break
            
    # Final pass for derivatives on the fully normalized dataset
    daily_pct_change, mad, sd = calculate_derivative_metrics(df)
    
    # Truncate the technical indicators to match the final normalized dataframe length
    if not df.empty:
        cut_off_date = df.index[0]
        priceAvg50 = priceAvg50.loc[cut_off_date:]
        priceAvg200 = priceAvg200.loc[cut_off_date:]
        rsi14 = rsi14.loc[cut_off_date:]
        
    return df, {
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
        'sd': sd,
        'priceAvg50': priceAvg50,
        'priceAvg200': priceAvg200,
        'rsi14': rsi14
    }