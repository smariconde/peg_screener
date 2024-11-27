import streamlit as st
import pandas as pd
from data_processing import process_and_cache_data
from stock_analisys import analyze_stock, create_chart
import yfinance as yf
from sector_analisys import sector_relative_performance

@st.cache_data
def load_data():
    return list(process_and_cache_data())

def main():
    st.title("PEG Screener")
    st.sidebar.header("Sector Analisys")
    sector_analysis = st.sidebar.button(f"Analizar", type="primary")
    if sector_analysis:
        relative_prices, performance_fig = sector_relative_performance()
        st.plotly_chart(performance_fig)
        final_performance = relative_prices.iloc[-1].sort_values(ascending=False)
        st.dataframe(final_performance)


    # Usar session state para mantener los datos cargados
    if 'cached_data' not in st.session_state:
        # Inicializar el estado de carga solo la primera vez
        data_load_state = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Cargar datos con progreso detallado
        cached_data = None
        
        try:
            for progress, status, data in process_and_cache_data():
                progress_bar.progress(progress)
                status_text.text(status)
                if data is not None:
                    cached_data = data
            
            # Guardar en session state
            st.session_state.cached_data = cached_data
            
            # Limpiar los elementos de progreso
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            data_load_state.error('❌ Error loading data')
            st.error(f"Error details: {str(e)}")
            return
    
    # Usar los datos guardados en session state
    cached_data = st.session_state.cached_data
    
    if cached_data and len(cached_data) > 0:
        st.sidebar.subheader("Select a stock")
        total_stocks = len(cached_data.keys())
        st.sidebar.write(f"Found {total_stocks} stocks with recent gaps")
        selected_symbol = st.sidebar.pills("Stocks", list(cached_data.keys()))
        
        if selected_symbol:
            # Add parameter inputs in sidebar
            st.sidebar.subheader("Pattern Detection Parameters")
            window = st.sidebar.slider("Window Size", 3, 10, 3)
            trend_sensitivity = st.sidebar.slider("Trend Sensitivity", 0.0, 1.0, 0.1)
            high_slope_threshold = trend_sensitivity
            low_slope_threshold = trend_sensitivity

            df = cached_data[selected_symbol]['df']
            start_idx = cached_data[selected_symbol]['start_idx']
            stock = yf.Ticker(selected_symbol)

            logo_url = f"https://logo.clearbit.com/{stock.info.get('website', '').replace('http://', '').replace('https://', '').split('/')[0]}"
            try:
                col1, col2 = st.columns([1, 9], gap="small", vertical_alignment="center")
                with col1:
                    st.image(logo_url, width=100)
                with col2:
                    st.link_button("Finviz", f"https://finviz.com/quote.ashx?t={selected_symbol}&ty=c&ta=1&p=d")
            except:
                st.write("No logo available")
                st.link_button("Finviz", f"https://finviz.com/quote.ashx?t={selected_symbol}&ty=c&ta=1&p=d")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Company", stock.info.get('longName', selected_symbol))
                st.metric("Sector", stock.info.get('sector', 'N/A'))
                st.metric("Market Cap", f"${stock.info['marketCap']/1e9:.1f}B")
            with col2:             
                st.metric("Price", f"${df['Close'].iloc[-1]:.2f}")
                st.metric("Target Price", f"${stock.info.get('targetMeanPrice', 'N/A'):.2f}")
                st.metric("Volume Ratio", f"{df['volume_ratio'].iloc[-1]:.1f}x")
            with col3:
                st.metric("Gap Size", f"{df.loc[start_idx, 'pct_change']*100:.1f}%")
                st.metric("Days Since Gap", f"{(df.index[-1] - start_idx).days}")
                short_float = stock.info.get('shortPercentOfFloat')
                short_float_display = f"{short_float*100:.1f}%" if short_float is not None else "N/A"
                st.metric("Short Float", short_float_display)

            if st.button(f"Analizar {selected_symbol}", type="primary"):
                df, pattern = analyze_stock(df, start_idx, window, high_slope_threshold, low_slope_threshold)
                
                # Calcular variables necesarias
                current_price = df['Close'].iloc[-1]
                ma20 = df['ma_20'].iloc[-1]
                ma50 = df['ma_50'].iloc[-1]
                rsi = df['rsi'].iloc[-1]
                gap_support = df.loc[start_idx, 'Low']
                
                # Grafico
                fig, _ = create_chart(df, selected_symbol, start_idx)
                st.pyplot(fig)
                
                # Información principal en dos columnas
                col1, col2, col3 = st.columns([0.3, 0.35, 0.25], gap="small")
                
                with col1:
                    st.subheader(f"{selected_symbol} Analysis")
                    st.write(f"Pattern: {pattern}")
                    st.write(f"Gap Up Date: {start_idx.date()}")
                    st.write(f"Parameters: {window, high_slope_threshold, low_slope_threshold}")
                
                with col2:
                    st.subheader("Setup Quality")
                    
                    # Evaluación del setup con más criterios
                    setup_score = 0
                    setup_reasons = []
                    
                    # Precio y Medias Móviles (30 puntos)
                    if current_price > ma20:
                        setup_score += 15
                        setup_reasons.append("✅ Price above MA20")
                        if current_price > ma50:
                            setup_score += 15
                            setup_reasons.append("✅ Price above MA50")
                    else:
                        setup_reasons.append("❌ Price below MA20")
                    
                    # Gap Support (20 puntos)
                    if current_price > gap_support:
                        setup_score += 20
                        setup_reasons.append("✅ Holding gap level")
                    else:
                        setup_reasons.append("❌ Lost gap support")
                    
                    # RSI (20 puntos) - Nuevo análisis de tendencia
                    rsi_trend = df['rsi'].iloc[-5:].diff().mean()  # Media de cambio en últimos 5 días
                    if 40 < rsi < 70 and rsi_trend > 0:
                        setup_score += 20
                        setup_reasons.append("✅ RSI rising in healthy range")
                    elif 40 < rsi < 70:
                        setup_score += 10
                        setup_reasons.append("⚠️ RSI stable in healthy range")
                    else:
                        setup_reasons.append("❌ RSI out of healthy range")
                    
                    # Volumen (20 puntos)
                    recent_volume = df['Volume'].iloc[-5:].mean()
                    avg_volume = df['Volume'].iloc[-20:].mean()
                    if recent_volume > avg_volume:
                        setup_score += 20
                        setup_reasons.append("✅ Above average volume")
                    else:
                        setup_reasons.append("❌ Below average volume")
                    
                    # MACD (10 puntos)
                    try:
                        if df['histogram'].iloc[-1] > 0:
                            setup_score += 10
                            setup_reasons.append("✅ Positive MACD")
                        else:
                            setup_reasons.append("❌ Negative MACD")
                    except (KeyError, AttributeError, IndexError):
                        # Skip MACD analysis if data is not available
                        setup_reasons.append("⚠️ MACD data not available")
                    
                    # Mostrar Score y Calificación
                    st.progress(setup_score/100)
                    
                    if setup_score >= 80:
                        st.success(f"Strong Setup ({setup_score}/100)")
                    elif setup_score >= 60:
                        st.warning(f"Moderate Setup ({setup_score}/100)")
                    else:
                        st.error(f"Weak Setup ({setup_score}/100)")
                with col3:
                    # Mostrar razones
                    st.write("Setup Analysis:")
                    for reason in setup_reasons:
                        st.write(reason)

                st.subheader("Recent Data")
                st.dataframe(df.tail())
    else:
        st.error('❌ No stocks found matching the criteria')
        st.write("Possible reasons:")
        st.write("- Market conditions might not be favorable for gaps")
        st.write("- Filtering criteria might be too strict")
        
        # Mostrar los criterios actuales
        st.write("\nCurrent filtering criteria:")
        st.write("- Minimum Market Cap: $5B")
        st.write("- Minimum Gap Size: 5%")
        st.write("- Minimum Average Volume: 500,000")
        
        # Sugerir ajustes
        st.write("\nTry adjusting the filtering criteria in data_processing.py:")
        st.code("""
        market_cap_min=5000000000  # Try lowering this
        gap_percent=5              # Try lowering this
        avg_volume=500000          # Try lowering this
        """)
        

if __name__ == "__main__":
    main()
