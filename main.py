import os
import yfinance as yf
import pandas as pd
import numpy as np
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import MACD
from scipy.signal import argrelextrema

def get_symbols():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    table = pd.read_html(url, header=0)[0]
    return list(table['Symbol'])

def get_stock_data(symbol, period='ytd'):
    stock = yf.Ticker(symbol)
    df = stock.history(period=period)
    return df

def calculate_rsi(df, window=14):
    rsi_indicator = RSIIndicator(df['Close'], window=window)
    df['rsi'] = rsi_indicator.rsi()
    return df

def calculate_macd(df):
    macd = MACD(df['Close'])
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['histogram'] = macd.macd_diff()
    return df

def filter_stocks(symbols, market_cap_min=5000000000, gap_percent=5):
    filtered_stocks = []
    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Check if marketCap is available, otherwise use a default value
            market_cap = info.get('marketCap', 0)
            
            if market_cap < market_cap_min:
                continue
            
            df = get_stock_data(symbol, period='1mo')
            df['pct_change'] = df['Close'].pct_change()
            gap_up_idx = df[df['pct_change'] >= gap_percent / 100].index
            
            if len(gap_up_idx) > 0:
                last_gap_up = gap_up_idx[-1]
                filtered_stocks.append((symbol, last_gap_up))
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
    
    return filtered_stocks

def identify_pattern(df, start_idx, window=3, high_slope_threshold=0.05, low_slope_threshold=0.05):
    df = df.loc[start_idx:].copy()
    df['High_smooth'] = df['High'].rolling(window=window).mean()
    df['Low_smooth'] = df['Low'].rolling(window=window).mean()
    
    # Find local maxima and minima
    high_extrema = argrelextrema(df['High_smooth'].values, np.greater, order=window)[0]
    low_extrema = argrelextrema(df['Low_smooth'].values, np.less, order=window)[0]
    
    if len(high_extrema) < 2 or len(low_extrema) < 2:
        return 'No clear pattern', None, None
    
    # Get the last two highs and lows
    last_two_highs = df['High_smooth'].iloc[high_extrema[-2:]].values
    last_two_lows = df['Low_smooth'].iloc[low_extrema[-2:]].values
    
    # Calculate slopes
    high_slope = (last_two_highs[1] - last_two_highs[0]) / (high_extrema[-1] - high_extrema[-2])
    low_slope = (last_two_lows[1] - last_two_lows[0]) / (low_extrema[-1] - low_extrema[-2])
    
    # Identify patterns using the thresholds
    if abs(high_slope) < high_slope_threshold and abs(low_slope) < low_slope_threshold:
        pattern = 'Rectangle'
    elif high_slope < -high_slope_threshold and low_slope > low_slope_threshold:
        pattern = 'Ascending Triangle' if high_slope > low_slope else 'Descending Triangle'
    elif high_slope < -high_slope_threshold and low_slope < -low_slope_threshold:
        pattern = 'Falling Wedge' if high_slope < low_slope else 'Descending Channel'
    elif high_slope > high_slope_threshold and low_slope > low_slope_threshold:
        pattern = 'Rising Wedge' if high_slope > low_slope else 'Ascending Channel'
    else:
        pattern = 'No clear pattern'
    
    return pattern, high_extrema, low_extrema

def chart(df, symbol, start_idx):
    df['ma_20'] = df['Close'].rolling(window=20).mean()
    
    pattern, high_extrema, low_extrema = identify_pattern(df.loc[start_idx:], start_idx)
    
    ap2 = [
        mpf.make_addplot(df['ma_20'], panel=0, color='orange', secondary_y=False),
        mpf.make_addplot(df['rsi'], panel=2, color='blue', secondary_y=False),
        mpf.make_addplot(df['macd'], panel=3, color='cyan', secondary_y=False),
        mpf.make_addplot(df['signal'], panel=3, color='purple', secondary_y=False),
        mpf.make_addplot(df['histogram'], panel=3, type='bar', width=0.7, color='grey', alpha=0.5, secondary_y=False)
    ]
    
    # Add pattern lines to the chart
    if pattern != 'No clear pattern' and high_extrema is not None and low_extrema is not None:
        high_line = pd.Series(index=df.index, dtype=float)
        low_line = pd.Series(index=df.index, dtype=float)
        
        # Adjust high_extrema and low_extrema indices to match the full DataFrame
        high_extrema += df.index.get_loc(start_idx)
        low_extrema += df.index.get_loc(start_idx)
        
        high_line.iloc[high_extrema[-2]:] = np.linspace(df['High'].iloc[high_extrema[-2]], df['High'].iloc[high_extrema[-1]], len(high_line.iloc[high_extrema[-2]:]))
        low_line.iloc[low_extrema[-2]:] = np.linspace(df['Low'].iloc[low_extrema[-2]], df['Low'].iloc[low_extrema[-1]], len(low_line.iloc[low_extrema[-2]:]))
        ap2.extend([
            mpf.make_addplot(high_line, panel=0, color='g', linestyle='--', secondary_y=False),
            mpf.make_addplot(low_line, panel=0, color='r', linestyle='--', secondary_y=False)
        ])
    
    # Add a vertical line to mark the gap up point
    gap_up_line = pd.Series(index=df.index, dtype=float)
    gap_up_price = max(df.loc[start_idx, 'Open'], df.loc[start_idx, 'Close'])
    gap_up_line.loc[:start_idx] = np.nan
    gap_up_line.loc[start_idx:] = gap_up_price
    ap2.append(mpf.make_addplot(gap_up_line, panel=0, color='blue', linestyle=':', secondary_y=False))
    
    # Create the charts directory if it doesn't exist
    os.makedirs('charts', exist_ok=True)

    mpf.plot(df, type='candle', style='yahoo', volume=True, savefig=f'charts/{symbol}.png', addplot=ap2,
            title=f'{symbol} - {pattern} (Gap Up: {start_idx.date()})',
            ylabel='Daily',
            ylabel_lower='',
            figratio=(30,15),
            figscale=1.5,
            panel_ratios=(6,1,2,2),
            tight_layout=True,
            volume_panel=1,
            scale_width_adjustment=dict(volume=0.7, candle=1.2),
            update_width_config=dict(candle_linewidth=1.2),
            block=False,
            datetime_format='%b %Y',
            xrotation=0)

def main():
    # List of stock symbols to analyze
    symbols = get_symbols()
    
    filtered_stocks = filter_stocks(symbols)
    
    for symbol, start_idx in filtered_stocks:
        try:
            df = get_stock_data(symbol)
            df = calculate_rsi(df)
            df = calculate_macd(df)
            
            pattern, _, _ = identify_pattern(df.loc[start_idx:], start_idx)
            
            print(f"Symbol: {symbol}")
            print(f"Pattern: {pattern}")
            print(f"Gap Up Date: {start_idx.date()}")
            print(df.loc[start_idx:].tail())
            print("\n")
            
            chart(df, symbol, start_idx)
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")

if __name__ == "__main__":
    main()