import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Battery Storage Analysis")

def calculate_cashflows(params):
    """Calculate annual cash flows and financial metrics"""
    total_system_cost = params['battery_capacity_kwh'] * params['system_cost_per_kwh']
    
    # Calculate peak reduction
    power_limited_reduction = min(params['battery_power_kw'], params['peak_load_kw'])
    energy_limited_reduction = min(
        params['battery_capacity_kwh'] * 0.9 / params['peak_duration_hours'],
        params['peak_load_kw']
    )
    actual_peak_reduction = min(power_limited_reduction, energy_limited_reduction)
    
    # Calculate annual savings
    monthly_savings = actual_peak_reduction * params['peak_demand_charge']
    annual_savings = monthly_savings * 12
    
    # Generate cash flows
    years = range(params['analysis_years'] + 1)
    cash_flows = [-total_system_cost]  # Initial investment
    cash_flows.extend([annual_savings] * params['analysis_years'])
    
    # Calculate cumulative NPV for each year
    discount_rate = 0.08  # 8% discount rate
    npv_values = []
    running_npv = -total_system_cost
    
    for year in years:
        if year == 0:
            npv_values.append(running_npv)
        else:
            running_npv += annual_savings / ((1 + discount_rate) ** year)
            npv_values.append(running_npv)
    
    # Calculate IRR
    irr = np.irr(cash_flows)
    
    # Find payback period
    payback_period = None
    for i, npv in enumerate(npv_values):
        if npv >= 0:
            payback_period = i
            break
    
    return {
        'years': years,
        'npv_values': npv_values,
        'annual_savings': annual_savings,
        'total_system_cost': total_system_cost,
        'peak_reduction': actual_peak_reduction,
        'irr': irr if irr is not None else 0,
        'payback_period': payback_period if payback_period is not None else float('inf')
    }

# Page Title
st.title("Battery Storage Peak Shaving Analysis")

# Sidebar with input parameters
st.sidebar.header("System Parameters")

params = {
    'peak_load_kw': st.sidebar.number_input("Peak Load (kW)", min_value=10, max_value=1000, value=72),
    'peak_duration_hours': st.sidebar.number_input("Peak Duration (hours)", min_value=0.5, max_value=8.0, value=2.5),
    'battery_power_kw': st.sidebar.number_input("Battery Power (kW)", min_value=10, max_value=1000, value=60),
    'battery_capacity_kwh': st.sidebar.number_input("Battery Capacity (kWh)", min_value=10, max_value=2000, value=210),
    'peak_demand_charge': st.sidebar.number_input("Peak Demand Charge ($/kW)", min_value=5, max_value=50, value=22),
    'system_cost_per_kwh': st.sidebar.number_input("System Cost ($/kWh)", min_value=100, max_value=1000, value=426),
    'analysis_years': st.sidebar.slider("Analysis Period (years)", min_value=5, max_value=30, value=15)
}

# Calculate results
results = calculate_cashflows(params)

# Create two columns for metrics
col1, col2 = st.columns(2)

with col1:
    st.metric("Total System Cost", f"${results['total_system_cost']:,.0f}")
    st.metric("Annual Savings", f"${results['annual_savings']:,.0f}")

with col2:
    st.metric("Peak Reduction", f"{results['peak_reduction']:.1f} kW")
    st.metric("Simple Payback", f"{results['payback_period']:.1f} years")
    st.metric("IRR", f"{results['irr']*100:.1f}%")

# Create cash flow visualization
fig = go.Figure()

# Add NPV line
fig.add_trace(go.Scatter(
    x=results['years'],
    y=results['npv_values'],
    mode='lines+markers+text',
    name='Cumulative NPV',
    text=[f"${x:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}" for x in results['npv_values']],
    textposition="top center",
    textfont=dict(size=10),
    line=dict(color='#2563eb', width=2)
))

# Add payback period vertical line
if results['payback_period'] != float('inf'):
    fig.add_vline(
        x=results['payback_period'],
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Payback: {results['payback_period']:.2f} years"
    )

# Update layout
fig.update_layout(
    title="Project Cash Flows",
    xaxis_title="Year",
    yaxis_title="Net Present Value ($)",
    showlegend=True,
    height=600,
    template="plotly_white",
    hovermode='x unified'
)

# Add zero line
fig.add_hline(y=0, line_dash="dot", line_color="gray")

# Show the plot
st.plotly_chart(fig, use_container_width=True)

# Add explanatory text
st.markdown("""
### Analysis Details
- The model calculates both power-limited and energy-limited peak reduction
- Uses 8% discount rate for NPV calculations
- Assumes consistent monthly peak demand charges
- Includes 90% round-trip battery efficiency
- All costs and savings are in current dollars
""")
