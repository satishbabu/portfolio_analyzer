import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from yahoo_interface import YahooInterface
from portfolio_ai_analyzer import PortfolioAIAnalyzer

st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Portfolio Analyzer")
st.markdown("Upload your portfolio CSV file to analyze your investments (stocks and options)")

# Initialize interfaces
yahoo = YahooInterface()

# Initialize session state
if 'portfolio_data' not in st.session_state:
    st.session_state.portfolio_data = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# File uploader
uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=['csv'],
    help="CSV should contain columns: 'Symbol' (stock ticker or option in format 'TICKER MM/DD/YYYY STRIKE C/P'), 'Shares' (number of shares), and optionally 'Purchase Price'"
)

def process_portfolio(uploaded_file):
    """Process uploaded portfolio CSV and fetch prices."""
    try:
        # Read CSV file
        df = pd.read_csv(uploaded_file)
        
        # Validate required columns
        required_columns = ['Symbol', 'Shares']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
            st.info("Please ensure your CSV has 'Symbol' and 'Shares' columns")
            return None
        
        # Clean data
        df = df.dropna(subset=['Symbol', 'Shares'])
        df['Symbol'] = df['Symbol'].str.upper().str.strip()
        df['Shares'] = pd.to_numeric(df['Shares'], errors='coerce')
        df = df.dropna(subset=['Shares'])
        
        if len(df) == 0:
            st.error("❌ No valid data found after cleaning")
            return None
        
        # Fetch current prices from Yahoo Finance
        st.subheader("🔄 Fetching Current Prices...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        prices = {}
        errors = []
        
        unique_symbols = df['Symbol'].unique()
        for idx, symbol in enumerate(unique_symbols):
            status_text.text(f"Fetching {symbol}...")
            price, error = yahoo.fetch_price(symbol)
            
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
            
            # Add underlying ticker column for grouping options with stocks
            df['Underlying Ticker'] = df['Symbol'].apply(yahoo.get_underlying_ticker)
            
            # Calculate total portfolio value
            total_value = df['Current Value'].sum()
            
            # Calculate percentage for each investment
            df['Percentage'] = (df['Current Value'] / total_value * 100).round(2)
            
            # Store in session state
            st.session_state.portfolio_data = {
                'df': df,
                'total_value': total_value,
                'summary_stats': {
                    'total_investments': len(df),
                    'average_holding': total_value / len(df) if len(df) > 0 else 0
                }
            }
            
            return st.session_state.portfolio_data
        else:
            st.error("❌ Could not fetch any prices. Please check your internet connection and symbols.")
            return None
    
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)
        return None

def display_portfolio_analysis(portfolio_data):
    """Display portfolio analysis visualization."""
    df = portfolio_data['df']
    total_value = portfolio_data['total_value']
    
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
    
    # Prepare data for pie chart - group by underlying ticker
    pie_data = df.groupby('Underlying Ticker').agg({
        'Current Value': 'sum'
    }).reset_index()
    pie_data = pie_data.rename(columns={'Underlying Ticker': 'Symbol'})
    # Recalculate percentages after grouping
    pie_data['Percentage'] = (pie_data['Current Value'] / total_value * 100).round(2)
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

def display_ai_analysis():
    """Display AI analysis screen with chat interface."""
    st.subheader("🤖 AI Portfolio Analysis")
    
    if st.session_state.portfolio_data is None:
        st.info("👆 Please upload and analyze a portfolio in the 'Portfolio Analysis' tab first.")
        return
    
    # Initialize AI analyzer
    ai_analyzer = PortfolioAIAnalyzer()
    
    # Check if API key is configured
    if not ai_analyzer.client:
        st.warning("⚠️ OpenAI API key not configured.")
        st.info("""
        To use AI analysis, please configure your OpenAI API key using one of these methods:
        1. Create a `.env` file in the project root with: `OPENAI_API_KEY=your-api-key`
        2. Set environment variable: `export OPENAI_API_KEY='your-api-key'`
        3. Create a `.streamlit/secrets.toml` file with:
           ```
           [openai]
           api_key = "your-api-key"
           ```
        """)
        return
    
    # Display portfolio summary
    with st.expander("📋 View Portfolio Summary", expanded=False):
        portfolio_summary = ai_analyzer.format_portfolio_summary(st.session_state.portfolio_data)
        st.text(portfolio_summary)
    
    # Quick analysis button
    if st.button("🔍 Get Quick Portfolio Analysis", type="primary"):
        with st.spinner("Analyzing portfolio..."):
            portfolio_summary = ai_analyzer.format_portfolio_summary(st.session_state.portfolio_data)
            analysis = ai_analyzer.analyze_portfolio(portfolio_summary)
            
            # Add to chat history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': analysis,
                'type': 'quick_analysis'
            })
            st.rerun()
    
    # Chat interface
    st.markdown("---")
    st.subheader("💬 Ask Questions About Your Portfolio")
    
    # Display chat history
    for i, message in enumerate(st.session_state.chat_history):
        if message['role'] == 'user':
            with st.chat_message("user"):
                st.write(message['content'])
        elif message['role'] == 'assistant':
            with st.chat_message("assistant"):
                st.write(message['content'])
                if message.get('type') == 'quick_analysis':
                    st.caption("Quick Portfolio Analysis")
    
    # Chat input
    user_question = st.chat_input("Ask a question about your portfolio...")
    
    if user_question:
        # Add user question to chat history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_question
        })
        
        # Get AI response
        with st.spinner("Thinking..."):
            portfolio_summary = ai_analyzer.format_portfolio_summary(st.session_state.portfolio_data)
            response = ai_analyzer.ask_question(portfolio_summary, user_question)
            
            # Add to chat history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response
            })
        
        st.rerun()
    
    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

# Main app logic
if uploaded_file is not None:
    # Process portfolio if not already done or if file changed
    portfolio_data = process_portfolio(uploaded_file)
    
    if portfolio_data:
        # Create tabs
        tab1, tab2 = st.tabs(["📊 Portfolio Analysis", "🤖 AI Analysis"])
        
        with tab1:
            st.subheader("📋 Portfolio Data")
            st.dataframe(portfolio_data['df'], use_container_width=True)
            display_portfolio_analysis(portfolio_data)
        
        with tab2:
            display_ai_analysis()
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
