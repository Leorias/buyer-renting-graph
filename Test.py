import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 1. Use 'centered' layout so charts scale down automatically on mobile
st.set_page_config(page_title="Dynamic Home Buying Model", layout="centered")

# Inject Custom Mobile CSS for better padding and responsive metrics
st.markdown(
    """
    <style>
    /* Adjust overall padding for mobile devices */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        /* Make metric text slightly smaller on small screens */
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏡 Dynamic Home Purchase & Wealth Tracker")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Conditions")
starting_capital = st.sidebar.number_input(
    "Starting Capital (€)", value=10000, step=2500
)
base_monthly_savings = st.sidebar.number_input(
    "Monthly Savings (€)", value=300, step=100
)

st.sidebar.header("2. Target House & Loan")
house_price = st.sidebar.number_input(
    "Target House Price (€)", value=100000, step=25000
)
down_payment_pct = (
    st.sidebar.slider("Down Payment (%)", 5, 60, 40, step=5) / 100.0
)
house_appreciation_annual = (
    st.sidebar.slider("House Appreciation Rate (%/yr)", 0.0, 8.0, 2.5) / 100.0
)

# FLAGS
include_house_in_portfolio = st.sidebar.checkbox(
    "Include House Value in Buyer Portfolio Post-Purchase",
    value=True,
    help="When checked, the appreciated market value of the house is added directly to the Buyer's Portfolio value after purchase.",
)
include_rent_in_buyer_portfolio = st.sidebar.checkbox(
    "Include Rent Savings in Buyer Portfolio Post-Purchase",
    value=True,
    help="When checked, the monthly rent amount saved post-purchase is added into the buyer's monthly investment portfolio contributions alongside base savings.",
)

st.sidebar.header("3. Investment Market Returns")
annual_return = (
    st.sidebar.slider("Portfolio Annual Return (%)", 1.0, 12.0, 7.0) / 100.0
)

st.sidebar.header("4. Rent")
monthly_rent = st.sidebar.slider("Monthly Rent (€)", 0, 4000, 800)
yearly_rent_increase = (
    st.sidebar.slider("Yearly Rent Increase (%)", 0.0, 12.0, 1.5) / 100.0
)

time_horizon_years = st.sidebar.slider("Simulation Horizon (Years)", 5, 40, 15)

# --- MODEL CALCULATIONS ---
months = time_horizon_years * 12
monthly_return = (1 + annual_return) ** (1 / 12) - 1
monthly_house_appreciation = (1 + house_appreciation_annual) ** (1 / 12) - 1

# Initial target costs
total_upfront_needed = house_price * down_payment_pct

# Arrays to track wealth over time
buyer_liquid_portfolio = np.zeros(months + 1)
buyer_house_val = np.zeros(months + 1)
buyer_portfolio_val = np.zeros(months + 1)

renter_portfolio_val = np.zeros(months + 1)
buyer_rent_val = np.zeros(months + 1)
renter_rent_val = np.zeros(months + 1)

buyer_net_winnings = np.zeros(months + 1)
renter_net_winnings = np.zeros(months + 1)

# Initialize Month 0 with Starting Capital
renter_portfolio_val[0] = starting_capital
buyer_liquid_portfolio[0] = starting_capital
buyer_portfolio_val[0] = starting_capital
buyer_net_winnings[0] = starting_capital
renter_net_winnings[0] = starting_capital

house_purchased = False
purchase_month = None
current_house_value = house_price

for m in range(1, months + 1):
    # Rent increases annually at the start of each year after Year 1
    if m > 1 and (m - 1) % 12 == 0:
        monthly_rent += monthly_rent * yearly_rent_increase

    # --- RENTER TRACK ---
    renter_portfolio_val[m] = (
        renter_portfolio_val[m - 1] * (1 + monthly_return) + base_monthly_savings
    )
    renter_rent_val[m] = renter_rent_val[m - 1] - monthly_rent
    renter_net_winnings[m] = renter_portfolio_val[m] + renter_rent_val[m]

    # --- BUYER TRACK ---
    if not house_purchased:
        # Pre-purchase: portfolio grows with investments + base monthly savings
        buyer_liquid_portfolio[m] = (
            buyer_liquid_portfolio[m - 1] * (1 + monthly_return) + base_monthly_savings
        )
        buyer_rent_val[m] = buyer_rent_val[m - 1] - monthly_rent

        # Check if buyer portfolio can afford the down payment
        if buyer_liquid_portfolio[m] >= total_upfront_needed:
            house_purchased = True
            purchase_month = m
            # Deduct down payment from buyer liquid investments
            buyer_liquid_portfolio[m] -= total_upfront_needed
            buyer_rent_val[m] -= (house_price - total_upfront_needed)
            buyer_house_val[m] = current_house_value
    else:
        # Post-purchase: Appreciate house value monthly
        current_house_value *= (1 + monthly_house_appreciation)
        buyer_house_val[m] = current_house_value

        # Determine monthly portfolio contribution post-purchase
        current_savings = base_monthly_savings
        if include_rent_in_buyer_portfolio:
            current_savings += monthly_rent

        # Liquid investment portfolio growth
        buyer_liquid_portfolio[m] = (
            buyer_liquid_portfolio[m - 1] * (1 + monthly_return) + current_savings
        )
        buyer_rent_val[m] = buyer_rent_val[m - 1]  # No more rent paid

    # Total buyer portfolio calculation based on UI flag
    if include_house_in_portfolio:
        buyer_portfolio_val[m] = buyer_liquid_portfolio[m] + buyer_house_val[m]
    else:
        buyer_portfolio_val[m] = buyer_liquid_portfolio[m]

    # Net Winnings = Portfolio + Rent Impact
    buyer_net_winnings[m] = buyer_portfolio_val[m] + buyer_rent_val[m]

# --- RESULTS METRICS ---
col1, col2, col3 = st.columns(3)

with col1:
    if house_purchased:
        st.success(
            f"🎯 House Purchased in **Month {purchase_month}** (Year {round(purchase_month / 12, 1)})"
        )
    else:
        st.error("❌ Target down payment not reached within simulation horizon.")

with col2:
    st.metric(
        label="Required Down Payment", value=f"{total_upfront_needed:,.2f} €"
    )

with col3:
    diff = buyer_net_winnings[-1] - renter_net_winnings[-1]
    st.metric(
        label="Final Net Winnings Difference (Buyer - Renter)",
        value=f"{diff:,.2f} €",
        delta=f"{'Buyer ahead' if diff >= 0 else 'Renter ahead'}",
    )

# --- PLOTTING ---
df = pd.DataFrame(
    {
        "Month": np.arange(months + 1),
        "Year": np.arange(months + 1) / 12,
        "Buyer Portfolio": buyer_portfolio_val,
        "Buyer House Value": buyer_house_val,
        "Buyer Payed Rent": buyer_rent_val,
        "Buyer Winnings": buyer_net_winnings,
        "Renter Portfolio": renter_portfolio_val,
        "Renter Payed Rent": renter_rent_val,
        "Renter Winnings": renter_net_winnings,
    }
)

fig = go.Figure()

# Add Buyer Traces
fig.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Buyer Portfolio"],
        mode="lines",
        name="Buyer Total Portfolio",
        line=dict(color="#1E88E5", width=3),
    )
)

if include_house_in_portfolio:
    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Buyer House Value"],
            mode="lines",
            name="House Market Value",
            line=dict(color="#4CAF50", width=2, dash="dash"),
        )
    )

fig.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Buyer Payed Rent"],
        mode="lines",
        name="Buyer Payed Rent / Debt",
        line=dict(color="#D32F2F", width=1.5, dash="dot"),
    )
)
fig.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Buyer Winnings"],
        mode="lines",
        name="Buyer Winnings",
        line=dict(color="#FBC02D", width=2.5),
    )
)

# Add Renter Traces
fig.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Renter Portfolio"],
        mode="lines",
        name="Renter Portfolio",
        line=dict(color="#8E24AA", width=3),
    )
)
fig.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Renter Payed Rent"],
        mode="lines",
        name="Renter Payed Rent",
        line=dict(color="#BA68C8", width=1.5, dash="dot"),
    )
)
fig.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Renter Winnings"],
        mode="lines",
        name="Renter Winnings",
        line=dict(color="#FFA500", width=2.5),
    )
)

# Mark the purchase event
if house_purchased:
    fig.add_vline(
        x=purchase_month,
        line_width=1.5,
        line_dash="dash",
        line_color="red",
        annotation_text=f" House Purchased (Mo {purchase_month})",
        annotation_position="top left",
    )

# Optimize Plotly layout for mobile screens
fig.update_layout(
    title="Wealth Accumulation & Real Estate Progression",
    xaxis_title="Months",
    yaxis_title="Value (€)",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.5,
        xanchor="center",
        x=0.5
    ),
    margin=dict(l=10, r=10, t=40, b=40),
)
fig.update_yaxes(tickformat=",.2f")

st.plotly_chart(fig, use_container_width=True)