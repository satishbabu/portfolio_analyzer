import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import re

st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Portfolio Analyzer")
st.markdown("Upload your portfolio CSV file to analyze your investments (stocks and options)")

def is_option_symbol(symbol):
    """Check if symbol is in option format: TICKER MM/DD/YYYY STRIKE C/P"""
    # Pattern: TICKER MM/DD/YYYY STRIKE C or P
    pattern = r'^[A-Z]+\s+\d{2}/\d{2}/\d{4}\s+\d+\.?\d*\s+[CP]$'
    return bool(re.match(pattern, symbol))

def parse_option_symbol(symbol):
    """Parse option symbol format: TICKER MM/DD/YYYY STRIKE C/P
    Returns: (underlying_ticker, expiration_date, strike_price, option_type) or None
    """
    try:
        parts = symbol.split()
        if len(parts) != 4:
            return None
        
        underlying = parts[0]
        exp_date_str = parts[1]  # MM/DD/YYYY
        strike_str = parts[2]
        option_type = parts[3].upper()  # C or P
        
        # Parse expiration date
        exp_date = datetime.strptime(exp_date_str, '%m/%d/%Y')
        
        # Parse strike price
        strike = float(strike_str)
        
        return (underlying, exp_date, strike, option_type)
    except Exception:
        return None

def fetch_price(symbol):
    """Fetch price for either a stock or option symbol"""
    # Check if it's an option
    if is_option_symbol(symbol):
        parsed = parse_option_symbol(symbol)
        if parsed is None:
            return None, f"Invalid option format: {symbol}"
        
        underlying, exp_date, strike, option_type = parsed
        
        try:
            # Get the underlying ticker
            ticker = yf.Ticker(underlying)
            
            # Format expiration date as YYYY-MM-DD
            exp_date_str = exp_date.strftime('%Y-%m-%d')
            
            # Get option chain for the expiration date
            try:
                opt_chain = ticker.option_chain(exp_date_str)
            except Exception:
                # If exact date fails, try to get the nearest expiration
                expirations = ticker.options
                if not expirations:
                    return None, f"No option data available for {underlying}"
                
                # Find the closest expiration date
                exp_date_only = exp_date.date()
                closest_exp = None
                min_diff = None
                
                for exp in expirations:
                    exp_dt = datetime.strptime(exp, '%Y-%m-%d').date()
                    diff = abs((exp_dt - exp_date_only).days)
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_exp = exp
                
                if closest_exp:
                    opt_chain = ticker.option_chain(closest_exp)
                else:
                    return None, f"Could not find option expiration date for {symbol}"
            
            # Get calls or puts
            if option_type == 'C':
                options_df = opt_chain.calls
            else:
                options_df = opt_chain.puts
            
            # Find the option with matching strike price (with small tolerance for rounding)
            matching_options = options_df[abs(options_df['strike'] - strike) < 0.01]
            
            if matching_options.empty:
                return None, f"Option {symbol} not found (strike {strike} may not exist)"
            
            # Get the last price (or bid/ask midpoint if lastPrice is NaN)
            option_row = matching_options.iloc[0]
            price = option_row.get('lastPrice')
            
            # If lastPrice is NaN, use bid/ask midpoint
            if pd.isna(price) or price == 0:
                bid = option_row.get('bid', 0)
                ask = option_row.get('ask', 0)
                if bid > 0 and ask > 0:
                    price = (bid + ask) / 2
                elif bid > 0:
                    price = bid
                elif ask > 0:
                    price = ask
                else:
                    return None, f"Option {symbol} has no price data available"
            
            return float(price), None
            
        except Exception as e:
            return None, f"Error fetching option {symbol}: {str(e)}"
    else:
        # Regular stock
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.history(period="1d")
            
            if not info.empty:
                current_price = info['Close'].iloc[-1]
                return current_price, None
            else:
                return None, f"No data available for {symbol}"
        except Exception as e:
            return None, str(e)

# File uploader
uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=['csv'],
    help="CSV should contain columns: 'Symbol' (stock ticker or option in format 'TICKER MM/DD/YYYY STRIKE C/P'), 'Shares' (number of shares), and optionally 'Purchase Price'"
)

if uploaded_file is not None:
    try:
        # Read CSV file
        df = pd.read_csv(uploaded_file)
        
        # Display uploaded data
        st.subheader("📋 Portfolio Data")
        st.dataframe(df, use_container_width=True)
        
        # Validate required columns
        required_columns = ['Symbol', 'Shares']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
            st.info("Please ensure your CSV has 'Symbol' and 'Shares' columns")
        else:
            # Clean data
            df = df.dropna(subset=['Symbol', 'Shares'])
            df['Symbol'] = df['Symbol'].str.upper().str.strip()
            df['Shares'] = pd.to_numeric(df['Shares'], errors='coerce')
            df = df.dropna(subset=['Shares'])
            
            if len(df) == 0:
                st.error("❌ No valid data found after cleaning")
            else:
                # Fetch current prices from Yahoo Finance
                st.subheader("🔄 Fetching Current Prices...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                prices = {}
                errors = []
                
                unique_symbols = df['Symbol'].unique()
                for idx, symbol in enumerate(unique_symbols):
                    status_text.text(f"Fetching {symbol}...")
                    price, error = fetch_price(symbol)
                    
                    if price is not None:
                        prices[symbol] = price
                    else:
                        errors.append(f"{symbol}: {error}")
                    
                    progress_bar.progress((idx + 1) / len(unique_symbols))
                
                progress_bar.empty()
                status_text.empty()
                
                if errors:
                    st.warning("⚠️ Some symbols could not be fetched:")
                    for error in errors:
                        st.text(f"  • {error}")
                
                if prices:
                    # Calculate portfolio values
                    df['Current Price'] = df['Symbol'].map(prices)
                    df = df[df['Current Price'].notna()]
                    df['Current Value'] = df['Shares'] * df['Current Price']
                    
                    # Calculate total portfolio value
                    total_value = df['Current Value'].sum()
                    
                    # Calculate percentage for each investment
                    df['Percentage'] = (df['Current Value'] / total_value * 100).round(2)
                    
                    # Display portfolio summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Investments", len(df))
                    with col2:
                        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
                    with col3:
                        st.metric("Average Holding", f"${(total_value / len(df)):,.2f}")
                    
                    # Create pie chart
                    st.subheader("📈 Portfolio Distribution")
                    
                    # Prepare data for pie chart
                    pie_data = df.groupby('Symbol').agg({
                        'Current Value': 'sum',
                        'Percentage': 'sum'
                    }).reset_index()
                    pie_data = pie_data.sort_values('Current Value', ascending=False)
                    
                    # Create pie chart using Plotly
                    fig = px.pie(
                        pie_data,
                        values='Current Value',
                        names='Symbol',
                        title='Portfolio Distribution by Investment',
                        hover_data=['Percentage'],
                        labels={'Percentage': 'Percentage (%)'}
                    )
                    
                    fig.update_traces(
                        textposition='inside',
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>' +
                                    'Value: $%{value:,.2f}<br>' +
                                    'Percentage: %{customdata[0]:.2f}%<br>' +
                                    '<extra></extra>'
                    )
                    
                    fig.update_layout(
                        height=600,
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="middle",
                            y=0.5,
                            xanchor="left",
                            x=1.05
                        )
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display detailed breakdown
                    st.subheader("📊 Detailed Portfolio Breakdown")
                    display_df = df[['Symbol', 'Shares', 'Current Price', 'Current Value', 'Percentage']].copy()
                    display_df.columns = ['Symbol', 'Shares', 'Current Price ($)', 'Current Value ($)', 'Percentage (%)']
                    display_df = display_df.sort_values('Current Value ($)', ascending=False)
                    display_df['Current Price ($)'] = display_df['Current Price ($)'].apply(lambda x: f"${x:.2f}")
                    display_df['Current Value ($)'] = display_df['Current Value ($)'].apply(lambda x: f"${x:,.2f}")
                    display_df['Percentage (%)'] = display_df['Percentage (%)'].apply(lambda x: f"{x:.2f}%")
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Download option
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Analyzed Portfolio (CSV)",
                        data=csv,
                        file_name=f"portfolio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("❌ Could not fetch any prices. Please check your internet connection and symbols.")
    
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    # Show sample CSV format
    st.info("👆 Please upload a CSV file to get started")
    
    st.subheader("📝 Expected CSV Format")
    sample_data = {
        'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'QQQ 01/15/2027 380.00 C'],
        'Shares': [10, 5, 15, 20, 8, 5]
    }
    sample_df = pd.DataFrame(sample_data)
    st.dataframe(sample_df, use_container_width=True)
    st.info("💡 Options format: 'TICKER MM/DD/YYYY STRIKE C' (Call) or 'TICKER MM/DD/YYYY STRIKE P' (Put). Example: 'QQQ 01/15/2027 380.00 C'")
    
    # Provide sample CSV download
    sample_csv = sample_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Sample CSV Template",
        data=sample_csv,
        file_name="portfolio_template.csv",
        mime="text/csv"
    )

