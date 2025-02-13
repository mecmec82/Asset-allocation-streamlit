import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- Functions ---
@st.cache_data  # Cache data to improve performance
def get_historical_data(tickers, start_date, end_date):
    data = yf.download(tickers, start=start_date, end=end_date)
    return data['Adj Close']

def calculate_portfolio_performance(data, weights):
    if data is None:
        return None

    daily_returns = data.pct_change().dropna()
    portfolio_returns = (daily_returns * weights).sum(axis=1)
    cumulative_returns = (1 + portfolio_returns).cumprod() - 1
    return cumulative_returns

# --- Default values ---
DEFAULT_ASSETS = ['SPY', 'QQQ', 'GC=F', 'BTC-USD'] # QQQ for NASDAQ, GC=F for Gold, BTC-USD for Bitcoin
ASSET_NAMES = {
    'SPY': 'S&P 500 (SPY)',
    'QQQ': 'NASDAQ 100 (QQQ)',
    'GC=F': 'Gold (GC=F)',
    'BTC-USD': 'Bitcoin (BTC-USD)'
}
DEFAULT_TIMEFRAME_YEARS = 5

# --- Streamlit App ---
st.title('Investment Portfolio Allocation Dashboard')

st.sidebar.header('Portfolio Settings')

# 1. Asset Selection
selected_assets_names = st.sidebar.multiselect(
    'Select up to 4 Assets',
    options=DEFAULT_ASSETS,
    default=DEFAULT_ASSETS,
    format_func=lambda x: ASSET_NAMES.get(x, x) # Display friendly names
)

if len(selected_assets_names) > 4:
    st.sidebar.warning("You've selected more than 4 assets. Please select up to 4.")
    selected_assets_names = selected_assets_names[:4] # Limit to 4

selected_assets_tickers = selected_assets_names


# 2. Timeframe Adjustment
today = pd.to_datetime('today')
start_date = st.sidebar.date_input(
    'Start Date',
    today - pd.DateOffset(years=DEFAULT_TIMEFRAME_YEARS)
)
end_date = st.sidebar.date_input(
    'End Date',
    today
)

if start_date >= end_date:
    st.sidebar.error('Error: Start date must be before end date.')


# 3. Allocation Input
if selected_assets_tickers:
    st.sidebar.subheader('Allocation Weights (%)')
    weights = {}
    total_weight = 0
    for asset in selected_assets_tickers:
        weight = st.sidebar.slider(
            ASSET_NAMES.get(asset, asset), # Display friendly name
            min_value=0, max_value=100, value=int(100 / len(selected_assets_tickers)) if selected_assets_tickers else 0
        ) / 100.0
        weights[asset] = weight
        total_weight += weight

    # Normalize weights if they don't sum to 1 (optional, but good practice)
    if total_weight != 1.0 and len(weights) > 0:
        norm_factor = 1.0 / total_weight if total_weight > 0 else 1.0
        weights = {asset: weight * norm_factor for asset, weight in weights.items()}


    # --- Data Fetching and Calculation ---
    if start_date < end_date: # Only proceed if dates are valid
        asset_data = get_historical_data(selected_assets_tickers, start_date, end_date)

        if asset_data is not None and not asset_data.empty:
            portfolio_cumulative_returns = calculate_portfolio_performance(asset_data, pd.Series(weights))

            if portfolio_cumulative_returns is not None:
                # --- Visualization ---
                fig = px.line(
                    portfolio_cumulative_returns,
                    x=portfolio_cumulative_returns.index,
                    y=portfolio_cumulative_returns.values,
                    title=f'Portfolio Performance: {", ".join([ASSET_NAMES.get(asset, asset) for asset in selected_assets_tickers])}',
                    labels={'value': 'Cumulative Return', 'Date': 'Date'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Could not calculate portfolio performance. Please check data and weights.")
        else:
            st.error("Failed to fetch data for the selected assets and timeframe. Please check your selections.")
else:
    st.info("Please select assets to configure your portfolio.")
  
