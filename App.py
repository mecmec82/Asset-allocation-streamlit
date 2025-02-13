import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# --- Configuration ---
st.set_page_config(page_title="Portfolio Allocation Dashboard", page_icon=":chart_with_upwards_trend:")

# --- Sidebar ---
st.sidebar.header("Portfolio Settings")

# Asset Selection
default_assets = ["SPY", "QQQ", "GLD", "BTC-USD"]  # Default: SPY, NASDAQ (QQQ), Gold (GLD), Bitcoin (BTC-USD)
selected_assets = st.sidebar.multiselect(
    "Select Assets (Max 4)",
    default_assets,
    default=default_assets,
    max_selections=4
)

# Timeframe Selection
today = date.today()
default_start_date = today - timedelta(days=5 * 365)  # 5 years ago
start_date = st.sidebar.date_input("Start Date", default_start_date)
end_date = st.sidebar.date_input("End Date", today)

# Portfolio Allocation (Weights)
st.sidebar.subheader("Allocation Weights (%)")
asset_weights = {}
if selected_assets:
    remaining_weight = 100
    weights_assigned = 0
    for i, asset in enumerate(selected_assets):
        default_weight = 0  # Start with 0 default weights
        if i == 0:
            default_weight = 40  # Example default for the first asset
        elif i == 1:
            default_weight = 30
        elif i == 2:
            default_weight = 20
        elif i == 3:
            default_weight = 10

        weight = st.sidebar.number_input(
            f"{asset} Weight (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(default_weight), # Use float for default to avoid type issues
            step=1.0,
            format="%.1f"  # Format to one decimal place if needed, but integers are fine for percentages
        )
        asset_weights[asset] = weight
        weights_assigned += weight
        remaining_weight -= weight

    if weights_assigned > 100:
        st.sidebar.warning("Total allocation exceeds 100%. Please adjust.")
    elif weights_assigned < 100:
        st.sidebar.info(f"Consider adjusting weights. Current total: {weights_assigned}%")


# --- Main Panel ---
st.title("Portfolio Allocation Performance Dashboard")
st.write("Visualize the growth of your investment portfolio based on different asset allocations.")

if not selected_assets:
    st.warning("Please select at least one asset in the sidebar.")
else:
    if start_date >= end_date:
        st.error("Error: Start date must be before end date.")
    else:
        # --- Data Fetching ---
        @st.cache_data  # Cache data for performance
        def fetch_historical_data(tickers, start, end):
            data = yf.download(tickers, start=start, end=end)['Adj Close']
            return data

        try:
            data = fetch_historical_data(selected_assets, start_date, end_date)

            if data.empty:
                st.error("No data found for the selected assets and timeframe. Please check asset tickers or timeframe.")
            else:
                # --- Portfolio Calculation ---
                portfolio_value = pd.DataFrame(index=data.index)
                portfolio_value['Portfolio'] = 0.0

                # Normalize weights if they don't sum to 100 (optional, but good practice)
                total_weight = sum(asset_weights.values())
                normalized_weights = {}
                if total_weight > 0: # Avoid division by zero
                    for asset, weight in asset_weights.items():
                        normalized_weights[asset] = weight / total_weight if total_weight > 0 else 0
                else:
                    # If all weights are zero, distribute evenly
                    num_assets = len(selected_assets)
                    if num_assets > 0:
                        for asset in selected_assets:
                            normalized_weights[asset] = 100.0 / num_assets

                initial_investment = 10000  # Example initial investment

                for asset in selected_assets:
                    if asset in normalized_weights: # Make sure asset has a weight defined
                        weight_percentage = normalized_weights[asset] / 100.0
                        portfolio_value['Portfolio'] += data[asset] * weight_percentage

                # Normalize portfolio to start at initial investment value
                first_day_portfolio_value = portfolio_value['Portfolio'].iloc[0]
                portfolio_value['Portfolio'] = (portfolio_value['Portfolio'] / first_day_portfolio_value) * initial_investment

                # --- Plotting ---
                fig = px.line(portfolio_value, x=portfolio_value.index, y='Portfolio',
                              title=f'Portfolio Performance ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})',
                              labels={'Portfolio': 'Portfolio Value ($)', 'Date': 'Date'})
                st.plotly_chart(fig, use_container_width=True)

                # --- Performance Metrics (Optional) ---
                st.subheader("Portfolio Performance Metrics (Example)")
                returns = portfolio_value['Portfolio'].pct_change().dropna()
                cumulative_return = (portfolio_value['Portfolio'].iloc[-1] / portfolio_value['Portfolio'].iloc[0]) - 1
                annual_return = (1 + cumulative_return)**(252/len(returns)) - 1 if len(returns) > 0 else 0 # Assuming 252 trading days per year
                stdev = returns.std()
                sharpe_ratio = annual_return / stdev if stdev > 0 else 0 # Assuming risk-free rate is 0 for simplicity

                col1, col2, col3 = st.columns(3)
                col1.metric("Cumulative Return", f"{cumulative_return*100:.2f}%")
                col2.metric("Annualized Return", f"{annual_return*100:.2f}%")
                col3.metric("Volatility (Std Dev)", f"{stdev*100:.2f}%")
                st.write(f"Sharpe Ratio (assuming risk-free rate of 0): **{sharpe_ratio:.2f}**")


        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.error("Please ensure asset tickers are correct and there is data available for the selected timeframe.")
