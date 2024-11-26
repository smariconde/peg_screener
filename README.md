# Stock Pattern Screener

A Streamlit-based web application that screens stocks for technical patterns and fundamental metrics, helping traders identify potential trading opportunities.

## Features

- **Real-time Stock Data**: Fetches current market data using yfinance
- **Technical Analysis**:
  - Pattern Detection for market trends
  - MACD indicator analysis
  - Visual charts from FinViz
- **Fundamental Metrics**:
  - PEG Ratio
  - Short Float percentage
  - Company information
- **User-Friendly Interface**:
  - Interactive parameter settings
  - Clear scoring system
  - Visual feedback for analysis results

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/peg_screener.git
cd peg_screener
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Access the application through your web browser (typically http://localhost:8501)

3. Select a stock symbol and adjust the pattern detection parameters:
   - Window Size (3-10)
   - Trend Sensitivity (0.0-2.0)

## Dependencies

- streamlit
- yfinance
- pandas
- numpy
- plotly

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
