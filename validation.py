from skopt import gp_minimize
from skopt.space import Integer, Real
from skopt.utils import use_named_args
from stock_analisys import identify_pattern
from data_processing import process_and_cache_data
from tqdm import tqdm

data_list = list(process_and_cache_data())
data = data_list[-1][1]

# Lista de tickers
tickers = list(data.keys())

# Espacio de búsqueda para los parámetros
search_space = [
    Integer(3, 20, name='window'),  # Tamaño de la ventana de rolling mean
    Real(0.01, 0.1, name='high_slope_threshold'),  # Umbral pendiente alta
    Real(0.01, 0.1, name='low_slope_threshold')   # Umbral pendiente baja
]

# Define la función objetivo para optimizar
@use_named_args(search_space)
def objective(**params):
    window = params['window']
    high_slope_threshold = params['high_slope_threshold']
    low_slope_threshold = params['low_slope_threshold']
    
    # Puntaje acumulado en todas las acciones
    total_score = 0
    count = 0

    for ticker in tickers:
        df = data[ticker]['df']
        start_idx = data[ticker]['start_idx']

        # Llama a tu función identify_pattern con los parámetros
        pattern, high_extrema, low_extrema = identify_pattern(df, start_idx, window, high_slope_threshold, low_slope_threshold)

        # Evalúa el resultado
        if pattern == 'No clear pattern':
            score = 0  # Penaliza la ausencia de patrones detectados
        else:
            # Asigna puntuaciones basadas en la calidad del patrón
            if pattern in ['Rectangle', 'Ascending Triangle', 'Descending Triangle']:
                score = 0.5
            elif pattern in ['Rising Wedge', 'Falling Wedge']:
                score = 0.8
            elif pattern in ['Ascending Channel', 'Descending Channel']:
                score = 1.0
            else:
                score = 0.2

        total_score += score
        count += 1

    # Retorna el puntaje promedio (negativo porque queremos maximizar)
    return -total_score / count

# Ejecuta la optimización bayesiana con barra de progreso
print("Iniciando optimización...")
with tqdm(total=50, desc="Optimizando parámetros", leave=True) as pbar:
    def progress_callback(res):
        pbar.update(1)

    result = gp_minimize(
        func=objective,          # Función objetivo
        dimensions=search_space, # Espacio de parámetros
        n_calls=50,              # Número de iteraciones
        random_state=42,         # Semilla para reproducibilidad
        callback=[progress_callback]  # Actualiza la barra de progreso
    )

# Muestra los mejores parámetros encontrados
print("Mejores parámetros:")
print(f"window: {result.x[0]}")
print(f"high_slope_threshold: {result.x[1]}")
print(f"low_slope_threshold: {result.x[2]}")

# Aplica los mejores parámetros en identify_pattern para cada acción
best_window = result.x[0]
best_high_slope = result.x[1]
best_low_slope = result.x[2]

for ticker in tqdm(tickers, desc="Aplicando mejores parámetros"):
    df = data[ticker]['df']
    start_idx = data[ticker]['start_idx']
    pattern, high_extrema, low_extrema = identify_pattern(df, start_idx, best_window)
    print(f"Ticker: {ticker}, Mejor patrón encontrado: {pattern}")