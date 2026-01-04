import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Portfolio Analyzer")
st.markdown("Upload your portfolio CSV file to analyze your investments")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=['csv'],
    help="CSV should contain columns: 'Symbol' (stock ticker), 'Shares' (number of shares), and optionally 'Purchase Price'"
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
                st.subheader("🔄 Fetching Current Stock Prices...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                prices = {}
                errors = []
                
                for idx, symbol in enumerate(df['Symbol'].unique()):
                    try:
                        status_text.text(f"Fetching {symbol}...")
                        ticker = yf.Ticker(symbol)
                        info = ticker.history(period="1d")
                        
                        if not info.empty:
                            current_price = info['Close'].iloc[-1]
                            prices[symbol] = current_price
                        else:
                            errors.append(f"{symbol}: No data available")
                    except Exception as e:
                        errors.append(f"{symbol}: {str(e)}")
                    
                    progress_bar.progress((idx + 1) / len(df['Symbol'].unique()))
                
                progress_bar.empty()
                status_text.empty()
                
                if errors:
                    st.warning("⚠️ Some stocks could not be fetched:")
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
                    st.error("❌ Could not fetch any stock prices. Please check your internet connection and stock symbols.")
    
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    # Show sample CSV format
    st.info("👆 Please upload a CSV file to get started")
    
    st.subheader("📝 Expected CSV Format")
    sample_data = {
        'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
        'Shares': [10, 5, 15, 20, 8]
    }
    sample_df = pd.DataFrame(sample_data)
    st.dataframe(sample_df, use_container_width=True)
    
    # Provide sample CSV download
    sample_csv = sample_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Sample CSV Template",
        data=sample_csv,
        file_name="portfolio_template.csv",
        mime="text/csv"
    )

