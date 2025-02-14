import streamlit as st
import yahoo_fin.stock_info as si
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# --- Configuration ---
st.set_page_config(page_title="Portfolio Allocation Dashboard", page_icon=":chart_with_upwards_trend:")

# --- Sidebar ---
st.sidebar.header("Portfolio Settings")

# Asset Selection
default_assets = ["SPY", "IWM", "GDX", "BTC-USD", "TLT"]
selected_assets = st.sidebar.multiselect(
    "Select Assets (Max 5)",
    default_assets,
    default=default_assets,
    max_selections=5
)

# Timeframe Selection
today = date.today()
default_start_date = today - timedelta(days=5 * 365)
start_date = st.sidebar.date_input("Start Date", default_start_date)
end_date = st.sidebar.date_input("End Date", today)

# Portfolio Allocation (Weights) - Using Sliders with Rebalancing
st.sidebar.subheader("Allocation Weights (%)")
asset_weights = {}

if "asset_weights_state" not in st.session_state:
    st.session_state.asset_weights_state = {asset: 20.0 for asset in default_assets[:len(selected_assets)]} # Initialize with equal weights

if selected_assets:
    remaining_weight = 100.0
    weights_assigned = 0.0
    sliders = {} # To store sliders for potential updates

    for i, asset in enumerate(selected_assets):
        default_weight = st.session_state.asset_weights_state.get(asset, 0.0) # Get from state or default 0

        # Create Slider for each asset
        weight = st.sidebar.slider(
            f"{asset} Weight (%)",
            min_value=0.0,
            max_value=100.0,
            value=default_weight,
            step=1.0,
            key=f"weight_slider_{asset}", # Unique key for each slider
        )
        asset_weights[asset] = weight
        st.session_state.asset_weights_state[asset] = weight # Update session state


    # Rebalance Logic (after all sliders are read)
    current_total_weight = sum(asset_weights.values())
    weight_difference = 100.0 - current_total_weight

    if abs(weight_difference) > 1e-6: # Check if difference is significant (avoid tiny floating point errors)
        num_assets_to_adjust = len(selected_assets)
        if num_assets_to_adjust > 0:
            weight_increment = weight_difference / num_assets_to_adjust # Distribute equally for simplicity. Can improve logic.

            for asset in asset_weights:
                asset_weights[asset] += weight_increment
                asset_weights[asset] = max(0.0, min(100.0, asset_weights[asset])) # Keep weights within 0-100%
                st.session_state.asset_weights_state[asset] = asset_weights[asset] # Update session state


    # Display current weights (for verification)
    weights_assigned = sum(asset_weights.values())
    if weights_assigned > 100:
        st.sidebar.warning(f"Total allocation exceeds 100%: {weights_assigned:.2f}%. Weights might be slightly adjusted.")
    elif weights_assigned < 100:
        st.sidebar.info(f"Total allocation is less than 100%: {weights_assigned:.2f}%. Weights might be slightly adjusted.")
    else:
        st.sidebar.success(f"Total allocation is 100%: {weights_assigned:.2f}%")


# --- Main Panel ---
st.title("Portfolio Allocation Performance Dashboard")
st.write("Visualize portfolio growth based on asset allocations.")

if not selected_assets:
    st.warning("Please select at least one asset in the sidebar.")
elif start_date >= end_date:
    st.error("Error: Start date must be before end date.")
else:
    # --- Data Fetching ---
    @st.cache_data
    def fetch_historical_data(tickers, start, end):
        all_data = {}
        for ticker in tickers:
            try:
                data = si.get_data(ticker=ticker, start_date=start, end_date=end)
                if data is None or data.empty or 'adjclose' not in data.columns:
                    st.error(f"Data issue for {ticker}. Please check ticker/timeframe.")
                    return None
                all_data[ticker] = data['adjclose']
            except Exception as e:
                st.error(f"Error fetching data for {ticker}: {e}")
                return None

        if not all_data:
            return None
        combined_data = pd.DataFrame(all_data)
        st.write("### Fetched Data:")  # Debugging output
        st.write(combined_data)  # Debugging output
        return combined_data

    data_df = fetch_historical_data(selected_assets, start_date, end_date)

    if data_df is None:
        st.error("Data fetch failed for one or more assets. Check tickers/timeframe.")
    elif data_df.empty:
        st.error("No data available for the selected assets and timeframe.")
    else:
        data_df.columns = selected_assets

        # --- Portfolio Calculation (Corrected using returns) ---
        asset_returns = data_df.pct_change().dropna() # Calculate daily returns
        st.write("### Asset Returns:") # Debugging output
        st.write(asset_returns) # Debugging output

        portfolio_value = pd.DataFrame(index=asset_returns.index)
        portfolio_value['Portfolio'] = 0.0

        normalized_weights = {}
        total_weight_for_norm = sum(asset_weights.values()) # Use current slider values for normalization
        if total_weight_for_norm > 0:
             for asset, weight in asset_weights.items():
                 normalized_weights[asset] = weight / total_weight_for_norm
        else:
            num_assets = len(selected_assets)
            if num_assets > 0:
                for asset in selected_assets:
                    normalized_weights[asset] = 1.0 / num_assets


        initial_investment = 10000
        portfolio_value['Portfolio'].iloc[0] = initial_investment # Initialize portfolio value

        # Calculate portfolio value day by day using returns
        for i in range(1, len(portfolio_value)):
            daily_portfolio_return = 0
            for asset in selected_assets:
                if asset in normalized_weights:
                    daily_portfolio_return += asset_returns[asset].iloc[i-1] * normalized_weights[asset]
            portfolio_value['Portfolio'].iloc[i] = portfolio_value['Portfolio'].iloc[i-1] * (1 + daily_portfolio_return)

        st.write("### Portfolio Value:") # Debugging output
        st.write(portfolio_value) # Debugging output


        # --- Plotting ---
        fig = px.line(portfolio_value, x=portfolio_value.index, y='Portfolio',
                      title=f'Portfolio Performance ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})',
                      labels={'Portfolio': 'Portfolio Value ($)', 'Date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)

        # --- Performance Metrics ---
        st.subheader("Portfolio Performance Metrics")
        returns = portfolio_value['Portfolio'].pct_change().dropna()

        cumulative_return = (portfolio_value['Portfolio'].iloc[-1] / portfolio_value['Portfolio'].iloc[0]) - 1 if not portfolio_value.empty else 0
        annual_return = (1 + cumulative_return)**(252/len(returns)) - 1 if len(returns) > 0 else 0
        stdev = returns.std() if not returns.empty else 0
        sharpe_ratio = annual_return / stdev if stdev > 0 else 0

        # Drawdown Calculation
        rolling_max = portfolio_value['Portfolio'].cummax()
        drawdown = portfolio_value['Portfolio'] / rolling_max - 1.0
        max_drawdown = drawdown.min() if not drawdown.empty else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Cumulative Return", f"{cumulative_return*100:.2f}%" if not pd.isna(cumulative_return) else "NaN")
        col2.metric("Annualized Return", f"{annual_return*100:.2f}%" if not pd.isna(annual_return) else "NaN")
        col3.metric("Volatility (Std Dev)", f"{stdev*100:.2f}%" if not pd.isna(stdev) else "NaN")
        col4.metric("Max Drawdown", f"{max_drawdown*100:.2f}%" if not pd.isna(max_drawdown) else "NaN")

        st.write(f"Sharpe Ratio (assuming risk-free rate of 0): **{sharpe_ratio:.2f}**" if not pd.isna(sharpe_ratio) else f"Sharpe Ratio (assuming risk-free rate of 0): **NaN**")
