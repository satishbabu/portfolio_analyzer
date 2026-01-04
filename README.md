# Portfolio Analyzer

A Streamlit-based web application that analyzes your investment portfolio by importing CSV data, fetching real-time stock prices from Yahoo Finance, and visualizing your portfolio distribution with interactive pie charts.

## Features

- 📊 **CSV Import**: Upload your portfolio data in CSV format
- 💰 **Real-time Prices**: Automatically fetches current stock prices from Yahoo Finance
- 📈 **Interactive Pie Chart**: Visualize your portfolio distribution with Plotly charts
- 📋 **Detailed Breakdown**: View comprehensive portfolio statistics and holdings
- 📥 **Export Results**: Download analyzed portfolio data as CSV

## Requirements

- Python 3.7+
- Internet connection (for fetching stock prices)

## Installation

1. Clone or navigate to this repository:
```bash
cd portfolio_analyzer
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. The application will open in your default web browser (usually at `http://localhost:8501`)

3. Upload a CSV file with your portfolio data. The CSV should have the following format:
   - **Symbol**: Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)
   - **Shares**: Number of shares owned

4. The application will:
   - Fetch current stock prices from Yahoo Finance
   - Calculate the current value of each holding
   - Display a pie chart showing the percentage distribution
   - Show detailed portfolio breakdown

## CSV Format

Your CSV file should look like this:

```csv
Symbol,Shares
AAPL,10
GOOGL,5
MSFT,15
TSLA,20
AMZN,8
```

A sample CSV file (`sample_portfolio.csv`) is included in this repository for reference.

## Features in Detail

### Portfolio Analysis
- Calculates total portfolio value
- Shows percentage allocation for each investment
- Displays current price and value for each holding

### Visualization
- Interactive pie chart with hover details
- Percentage labels on chart segments
- Legend for easy identification

### Error Handling
- Validates CSV format and required columns
- Handles missing or invalid stock symbols gracefully
- Shows progress while fetching stock prices

## Dependencies

- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **yfinance**: Yahoo Finance API wrapper for fetching stock data
- **plotly**: Interactive visualization library

## Notes

- Stock prices are fetched in real-time from Yahoo Finance
- Ensure you have an active internet connection
- Stock symbols should be valid ticker symbols (e.g., AAPL for Apple Inc.)
- The application handles multiple entries of the same symbol by aggregating them
