import yfinance as yf
import pandas as pd
from datetime import datetime
import re


class YahooInterface:
    """Interface for fetching price data from Yahoo Finance for stocks and options."""
    
    def __init__(self):
        """Initialize the YahooInterface."""
        pass
    
    def fetch_price(self, symbol):
        """Fetch price for either a stock or option symbol.
        
        Args:
            symbol: Stock ticker or option symbol in format 'TICKER MM/DD/YYYY STRIKE C/P'
            
        Returns:
            tuple: (price, error_message) where price is float or None, error_message is str or None
        """
        # Check if it's an option
        if self._is_option_symbol(symbol):
            return self._fetch_option_price(symbol)
        else:
            return self._fetch_stock_price(symbol)
    
    def get_underlying_ticker(self, symbol):
        """Extract underlying ticker from symbol (for options) or return symbol itself (for stocks).
        
        Args:
            symbol: Stock ticker or option symbol
            
        Returns:
            str: Underlying ticker for options, or the symbol itself for stocks
        """
        if self._is_option_symbol(symbol):
            parsed = self._parse_option_symbol(symbol)
            if parsed:
                return parsed[0]  # Return the underlying ticker
        return symbol  # For stocks, return the symbol itself
    
    def _is_option_symbol(self, symbol):
        """Check if symbol is in option format: TICKER MM/DD/YYYY STRIKE C/P.
        
        Args:
            symbol: Symbol to check
            
        Returns:
            bool: True if symbol is in option format, False otherwise
        """
        # Pattern: TICKER MM/DD/YYYY STRIKE C or P
        pattern = r'^[A-Z]+\s+\d{2}/\d{2}/\d{4}\s+\d+\.?\d*\s+[CP]$'
        return bool(re.match(pattern, symbol))
    
    def _parse_option_symbol(self, symbol):
        """Parse option symbol format: TICKER MM/DD/YYYY STRIKE C/P.
        
        Args:
            symbol: Option symbol to parse
            
        Returns:
            tuple: (underlying_ticker, expiration_date, strike_price, option_type) or None
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
    
    def _fetch_stock_price(self, symbol):
        """Fetch price for a stock symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            tuple: (price, error_message) where price is float or None, error_message is str or None
        """
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
    
    def _fetch_option_price(self, symbol):
        """Fetch price for an option symbol.
        
        Args:
            symbol: Option symbol in format 'TICKER MM/DD/YYYY STRIKE C/P'
            
        Returns:
            tuple: (price, error_message) where price is float or None, error_message is str or None
        """
        parsed = self._parse_option_symbol(symbol)
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
            
            # Options contracts represent 100 shares, so multiply price by 100
            price = float(price) * 100
            
            return price, None
            
        except Exception as e:
            return None, f"Error fetching option {symbol}: {str(e)}"

