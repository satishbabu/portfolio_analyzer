from openai import OpenAI
from typing import Dict, List, Optional, Tuple
import json
import os
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env file from the project root directory
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass


class PortfolioAIAnalyzer:
    """AI-powered portfolio analyzer using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the PortfolioAIAnalyzer.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from .env file, environment variable, or Streamlit secrets.
        """
        self.api_key = api_key
        
        # Try to get API key from various sources (in order of priority)
        if not self.api_key:
            # 1. Try .env file (loaded via python-dotenv above)
            self.api_key = os.getenv('OPENAI_API_KEY')
        
        # 2. Try Streamlit secrets if available
        if not self.api_key:
            try:
                import streamlit as st
                if hasattr(st, 'secrets') and 'openai' in st.secrets and 'api_key' in st.secrets.openai:
                    self.api_key = st.secrets.openai.api_key
            except:
                pass
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def format_portfolio_summary(self, portfolio_df: Dict) -> str:
        """Format portfolio data into a readable summary for the AI.
        
        Args:
            portfolio_df: Dictionary containing portfolio data including:
                - df: DataFrame with portfolio holdings
                - total_value: Total portfolio value
                - summary_stats: Dictionary with summary statistics
                
        Returns:
            str: Formatted portfolio summary string
        """
        df = portfolio_df.get('df')
        total_value = portfolio_df.get('total_value', 0)
        summary_stats = portfolio_df.get('summary_stats', {})
        
        summary = f"""PORTFOLIO SUMMARY:
Total Portfolio Value: ${total_value:,.2f}
Total Number of Holdings: {len(df)}
Average Holding Value: ${total_value / len(df) if len(df) > 0 else 0:,.2f}

HOLDINGS DETAILS:
"""
        
        # Add each holding
        for _, row in df.iterrows():
            symbol = row.get('Symbol', 'N/A')
            shares = row.get('Shares', 0)
            current_price = row.get('Current Price', 0)
            current_value = row.get('Current Value', 0)
            percentage = row.get('Percentage', 0)
            underlying_ticker = row.get('Underlying Ticker', symbol)
            
            summary += f"- {symbol}: {shares} shares @ ${current_price:.2f} = ${current_value:,.2f} ({percentage:.2f}%)\n"
        
        # Add grouped by underlying ticker if available
        if 'Underlying Ticker' in df.columns:
            summary += "\nGROUPED BY UNDERLYING TICKER:\n"
            grouped = df.groupby('Underlying Ticker').agg({
                'Current Value': 'sum',
                'Shares': 'sum'
            }).reset_index()
            
            for _, row in grouped.iterrows():
                ticker = row['Underlying Ticker']
                value = row['Current Value']
                total_shares = row['Shares']
                pct = (value / total_value * 100) if total_value > 0 else 0
                summary += f"- {ticker}: ${value:,.2f} ({pct:.2f}%) - {total_shares} total shares\n"
        
        return summary
    
    def analyze_portfolio(self, portfolio_summary: str, question: Optional[str] = None) -> str:
        """Analyze portfolio using OpenAI API.
        
        Args:
            portfolio_summary: Formatted portfolio summary string
            question: Optional specific question to ask about the portfolio
            
        Returns:
            str: AI analysis response
        """
        if not self.client:
            return "Error: OpenAI API key not configured. Please set OPENAI_API_KEY in a .env file, environment variable, or Streamlit secrets."
        
        # Build the prompt
        system_prompt = """You are an expert stock analyst specializing in stock and options portfolio analysis, risk assessment, and investment strategy. 
Analyze the provided portfolio data and provide insightful, actionable recommendations. Consider:
- Portfolio diversification and concentration risk
- Sector exposure and market correlation
- Risk-return characteristics
- Potential improvements or concerns
- Overall portfolio health and balance
- Identify ETFs and look through the holdings of the ETF for diversification and concentration risk

Be specific, data-driven, and professional in your analysis."""
        
        if question:
            user_prompt = f"""Portfolio Information:
{portfolio_summary}

Question: {question}

Please provide a detailed analysis addressing the question above."""
        else:
            user_prompt = f"""Portfolio Information:
{portfolio_summary}

Please provide a comprehensive analysis of this portfolio, including:
1. Overall assessment
2. Risk analysis
3. Diversification assessment
4. Recommendations for improvement"""
        
        try:
            # Use OpenAI ChatCompletion API
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                reasoning_effort="minimal",  # Options: "minimal", "medium", "maximum"
                verbosity="low",           # Options: "low", "medium", "high"
                max_completion_tokens=2500
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"Error calling OpenAI API: {str(e)}"
    
    def ask_question(self, portfolio_summary: str, question: str) -> str:
        """Ask a specific question about the portfolio.
        
        Args:
            portfolio_summary: Formatted portfolio summary string
            question: User's question about the portfolio
            
        Returns:
            str: AI response to the question
        """
        return self.analyze_portfolio(portfolio_summary, question)

