import pandas as pd
import numpy as np
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import MACD
from scipy.signal import argrelextrema
import streamlit as st

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

def identify_pattern(df, start_idx, window=3, high_slope_threshold=0.05, low_slope_threshold=0.05):
    # Validación inicial de datos
    df = df.loc[start_idx:].copy()
    if len(df) < window * 2:
        return f'Insufficient data: need at least {window * 2} days, got {len(df)} days', None, None
    
    # Limpiar datos faltantes
    df = df.dropna()
    
    # Reducir el window para el smoothing para detectar más puntos
    smooth_window = max(2, window - 1)  # Reducir el window para el smoothing
    df['High_smooth'] = df['High'].rolling(window=smooth_window, min_periods=2).mean()
    df['Low_smooth'] = df['Low'].rolling(window=smooth_window, min_periods=2).mean()
    
    # Reducir el orden para encontrar más extremos locales
    order = max(1, window - 2)  # Reducir el orden para encontrar más puntos extremos
    high_extrema = argrelextrema(df['High_smooth'].fillna(method='ffill').values, np.greater, order=order)[0]
    low_extrema = argrelextrema(df['Low_smooth'].fillna(method='ffill').values, np.less, order=order)[0]
    
    # Si no hay suficientes puntos, intentar con un orden más pequeño
    if len(high_extrema) < 2 or len(low_extrema) < 2:
        order = 1  # Usar el orden mínimo
        high_extrema = argrelextrema(df['High_smooth'].fillna(method='ffill').values, np.greater, order=order)[0]
        low_extrema = argrelextrema(df['Low_smooth'].fillna(method='ffill').values, np.less, order=order)[0]
    
    # Si aún no hay suficientes puntos, usar los puntos más altos y más bajos
    if len(high_extrema) < 2 or len(low_extrema) < 2:
        # Encontrar los puntos más altos y más bajos manualmente
        high_values = df['High_smooth'].values
        low_values = df['Low_smooth'].values
        
        # Obtener índices de los 2 valores más altos y más bajos
        high_extrema = np.argsort(high_values)[-2:]
        low_extrema = np.argsort(low_values)[:2]
    
    # Usar los puntos para el análisis
    high_points = df['High_smooth'].iloc[high_extrema].values
    low_points = df['Low_smooth'].iloc[low_extrema].values
    
    # Calcular y normalizar pendientes
    price_range = df['High'].max() - df['Low'].min()
    if price_range == 0:
        return 'No price variation detected', None, None
        
    high_slope = np.polyfit(range(len(high_points)), high_points, 1)[0] / price_range
    low_slope = np.polyfit(range(len(low_points)), low_points, 1)[0] / price_range
    
    # Calcular score de confiabilidad
    confidence_score = calculate_confidence_score(df, high_slope, low_slope, high_extrema, low_extrema)
    
    # Identificar patrón con el score de confiabilidad
    pattern, confidence = identify_pattern_with_confidence(high_slope, low_slope, high_slope_threshold, confidence_score)
    
    return f"{pattern} (Confidence: {confidence:.1f}%)", high_extrema, low_extrema

def calculate_confidence_score(df, high_slope, low_slope, high_extrema, low_extrema):
    # Calcular score basado en varios factores
    score = 100.0
    
    # Factor 1: Consistencia de los puntos
    if len(high_extrema) < 4 or len(low_extrema) < 4:
        score *= 0.8
    
    # Factor 2: Volatilidad
    volatility = df['Close'].pct_change().std()
    if volatility > 0.02:  # Alta volatilidad
        score *= 0.9
    
    # Factor 3: Volumen
    avg_volume = df['Volume'].mean()
    recent_volume = df['Volume'].iloc[-5:].mean()
    if recent_volume < avg_volume * 0.7:
        score *= 0.85
    
    return max(min(score, 100), 0)  # Asegurar que está entre 0 y 100

def identify_pattern_with_confidence(high_slope, low_slope, threshold, confidence_score):
    base_confidence = confidence_score
    
    if abs(high_slope) < threshold and abs(low_slope) < threshold:
        return 'Rectangle/Consolidation', base_confidence * 0.9
    elif high_slope > threshold and low_slope < threshold:
        return 'Ascending Triangle', base_confidence
    elif high_slope < -threshold and low_slope > -threshold:
        return 'Descending Triangle', base_confidence
    elif high_slope < -threshold and low_slope < -threshold:
        pattern = 'Falling Wedge' if abs(high_slope) > abs(low_slope) else 'Descending Channel'
        return pattern, base_confidence * 0.95
    elif high_slope > threshold and low_slope > threshold:
        pattern = 'Rising Wedge' if high_slope > low_slope else 'Ascending Channel'
        return pattern, base_confidence * 0.95
    else:
        return 'No clear pattern', base_confidence * 0.5

def create_chart(df, symbol, start_idx):
    # Calcular indicadores antes de usarlos
    #df = calculate_rsi(df)
    df = calculate_macd(df)
    # df['ma_20'] = df['Close'].rolling(window=20).mean()
    
    # Obtener los parámetros actuales de la sesión de Streamlit
    window = st.session_state.get('window', 3)
    high_slope_threshold = st.session_state.get('high_slope_threshold', 0.003)
    low_slope_threshold = st.session_state.get('low_slope_threshold', 0.003)
    
    # Usar los mismos parámetros que en analyze_stock
    pattern, high_extrema, low_extrema = identify_pattern(
        df.loc[start_idx:], 
        start_idx,
        window=window,
        high_slope_threshold=high_slope_threshold,
        low_slope_threshold=low_slope_threshold
    )
    
    # Si hay error en el patrón, mostrar gráfico básico
    if isinstance(pattern, str) and pattern.startswith('Error'):
        ap2 = [mpf.make_addplot(df['ma_20'], panel=0, color='orange', secondary_y=False)]
    else:
        rsi_50_line = pd.Series(50, index=df.index)
        ap2 = [
            mpf.make_addplot(df['ma_20'], panel=0, color='yellow', secondary_y=False),
            mpf.make_addplot(df['ma_50'], panel=0, color='orange', secondary_y=False),
            mpf.make_addplot(df['rsi'], panel=2, color='blue', secondary_y=False),
            mpf.make_addplot(rsi_50_line, panel=2, color='red', linestyle='--', secondary_y=False),
            mpf.make_addplot(df['macd'], panel=3, color='cyan', secondary_y=False),
            mpf.make_addplot(df['signal'], panel=3, color='purple', secondary_y=False),
            mpf.make_addplot(df['histogram'], panel=3, type='bar', width=0.7, color='grey', alpha=0.5, secondary_y=False)
        ]
    
    if pattern != 'No clear pattern' and high_extrema is not None and low_extrema is not None:
        high_line = pd.Series(index=df.index, dtype=float)
        low_line = pd.Series(index=df.index, dtype=float)
        
        high_extrema += df.index.get_loc(start_idx)
        low_extrema += df.index.get_loc(start_idx)
        
        high_line.iloc[high_extrema[-2]:] = np.linspace(df['High'].iloc[high_extrema[-2]], df['High'].iloc[high_extrema[-1]], len(high_line.iloc[high_extrema[-2]:]))
        low_line.iloc[low_extrema[-2]:] = np.linspace(df['Low'].iloc[low_extrema[-2]], df['Low'].iloc[low_extrema[-1]], len(low_line.iloc[low_extrema[-2]:]))
        ap2.extend([
            mpf.make_addplot(high_line, panel=0, color='g', linestyle='--', secondary_y=False),
            mpf.make_addplot(low_line, panel=0, color='r', linestyle='--', secondary_y=False)
        ])
    
    gap_up_line = pd.Series(index=df.index, dtype=float)
    gap_up_price = max(df.loc[start_idx, 'Open'], df.loc[start_idx, 'Close'])
    gap_up_line.loc[:start_idx] = np.nan
    gap_up_line.loc[start_idx:] = gap_up_price
    ap2.append(mpf.make_addplot(gap_up_line, panel=0, color='blue', linestyle=':', secondary_y=False))
    
    fig, axes = mpf.plot(df, type='candle', style='yahoo', volume=True, addplot=ap2,
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
                         datetime_format='%b %Y',
                         xrotation=0,
                         returnfig=True)
    
    return fig, axes

def analyze_stock(df, start_idx, window=3, high_slope_threshold=0.05, low_slope_threshold=0.05):
    # Validar datos de entrada
    if df.empty:
        return df, "Error: Empty dataset"
    
    if start_idx not in df.index:
        return df, "Error: Invalid start date"
    
    min_required_days = max(window * 2, 10)  
    if len(df.loc[start_idx:]) < min_required_days:
        return df, f"Error: Need at least {min_required_days} days of data after gap up"
    
    #df = calculate_rsi(df)
    df = calculate_macd(df)
    pattern, _, _ = identify_pattern(df, start_idx, window, high_slope_threshold, low_slope_threshold)
    
    return df, pattern
