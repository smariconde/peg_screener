import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

def sector_relative_performance(period='1y'):
    """
    Genera gráfico de líneas con rendimiento relativo de sectores
    
    Args:
    - period (str): Período de análisis
    
    Returns:
    - DataFrame con precios normalizados
    - Figura de Plotly
    """
    sector_etfs = {
        'Technology': 'XLK',
        'Financials': 'XLF', 
        'Energy': 'XLE',
        'Healthcare': 'XLV',
        'Industrials': 'XLI',
        'Materials': 'XLB',
        'Consumer Discretionary': 'XLY',
        'Consumer Staples': 'XLP',
        'Utilities': 'XLU',
        'Communication Services': 'XLC'
    }
    
    # DataFrame para almacenar precios normalizados
    normalized_prices = pd.DataFrame()
    
    # Descargar y normalizar datos
    for sector, etf in sector_etfs.items():
        try:
            # Descargar datos
            data = yf.download(etf, period=period)
            
            if len(data) > 0:
                # Normalizar precios (primer precio = 100)
                normalized_sector = data[('Adj Close', etf)] / data[('Adj Close', etf)].iloc[0] * 100
                normalized_prices[sector] = normalized_sector
        
        except Exception as e:
            print(f"Error procesando {sector}: {e}")
    
    # Crear gráfico de líneas con Plotly
    fig = go.Figure()
    
    # Añadir línea para cada sector
    for sector in normalized_prices.columns:
        fig.add_trace(go.Scatter(
            x=normalized_prices.index, 
            y=normalized_prices[sector],
            mode='lines',
            name=sector,
            hovertemplate='%{y:.2f}%<extra></extra>'
        ))
    
    # Configurar layout
    fig.update_layout(
        title='Rendimiento Relativo de Sectores',
        xaxis_title='Fecha',
        yaxis_title='Rendimiento Relativo (Base 100)',
        template='plotly_white',
        hovermode='x unified'
    )
    
    # Añadir línea base en 100
    fig.add_shape(
        type='line',
        x0=normalized_prices.index[0],
        x1=normalized_prices.index[-1],
        y0=100,
        y1=100,
        line=dict(color='gray', width=1, dash='dash')
    )
    
    return normalized_prices, fig
