import yfinance as yf
import pandas as pd
from datetime import timedelta
from stock_analisys import calculate_rsi


def get_sp500_symbols():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    table = pd.read_html(url, header=0)[0]
    return list(table['Symbol'])

def get_stock_data(symbol, period='ytd'):
    stock = yf.Ticker(symbol)
    df = stock.history(period=period)

    df['volume_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['pct_change'] = df['Close'].pct_change()
    df['ma_20'] = df['Close'].rolling(window=20).mean()
    df['ma_50'] = df['Close'].rolling(window=50).mean()
    df = calculate_rsi(df)
    return df

def filter_stocks(symbols, market_cap_min=5000000000, gap_percent=5):
    filtered_stocks = []
    total = len(symbols)
    stocks_checked = 0
    stocks_filtered = 0
    
    for i, symbol in enumerate(symbols):
        try:
            stocks_checked += 1
            progress = (i + 1) / total
            status = (f"Filtering stocks: {i + 1}/{total} ({symbol})\n"
                     f"Passed filters: {len(filtered_stocks)}")
            
            stock = yf.Ticker(symbol)
            info = stock.info
            
            market_cap = info.get('marketCap', 0)
            avg_volume = info.get('averageVolume', 0)
            
            if market_cap < market_cap_min:
                stocks_filtered += 1
                continue
                
            if avg_volume < 500000:
                stocks_filtered += 1
                continue
            
            df = get_stock_data(symbol, period='1mo')
            
            gap_up_idx = df[
                (df['pct_change'] >= gap_percent / 100)
            ].index
            
            if len(gap_up_idx) > 0:
                last_gap_up = gap_up_idx[-1]
                filtered_stocks.append((symbol, last_gap_up))
                
            yield progress, status, None
                
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
            continue
    
    # Mostrar resumen final
    final_status = (f"\nFiltering complete:\n"
                   f"Total stocks checked: {stocks_checked}\n"
                   f"Stocks filtered out: {stocks_filtered}\n"
                   f"Stocks with gaps: {len(filtered_stocks)}")
    yield 1.0, final_status, filtered_stocks
    
    return filtered_stocks

def process_and_cache_data():
    symbols = get_sp500_symbols()
    cached_data = {}
    
    # Fase 1: Filtrado de stocks
    filtered_stocks = None
    for progress, status, result in filter_stocks(symbols):
        yield progress * 0.5, status, None
        # Capturar la lista final de stocks filtrados
        if status.startswith('\nFiltering complete'):
            filtered_stocks = result  # Aquí guardamos la lista, no el generador
    
    # Verificar si tenemos stocks filtrados
    if not filtered_stocks:
        yield 1.0, "No stocks found", {}
        return
    
    # Fase 2: Carga de datos históricos
    total_filtered = len(filtered_stocks)
    
    for i, (symbol, start_idx) in enumerate(filtered_stocks):
        try:
            progress = (i + 1) / total_filtered
            status = f"Loading historical data: {i + 1}/{total_filtered} ({symbol})"
            
            df = get_stock_data(symbol)
            cached_data[symbol] = {'df': df, 'start_idx': start_idx}
            
            yield 0.5 + (progress * 0.5), status, cached_data
            
        except Exception as e:
            print(f"Error loading data for {symbol}: {str(e)}")
            continue
    
    if not cached_data:
        yield 1.0, "No data loaded", {}
    else:
        yield 1.0, f"Loaded {len(cached_data)} stocks", cached_data
