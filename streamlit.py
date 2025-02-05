import streamlit as st
import pandas as pd
import numpy as np

def calculate_system_cost(params):
    """Calculate total system cost with separate battery and inverter components"""
    battery_cost = params['battery_capacity_kwh'] * params['battery_cost_per_kwh']
    inverter_cost = params['battery_power_kw'] * params['inverter_cost_per_kw']
    installation_cost = (battery_cost + inverter_cost) * params['installation_factor']
    
    return {
        'battery_cost': battery_cost,
        'inverter_cost': inverter_cost,
        'installation_cost': installation_cost,
        'total_cost': battery_cost + inverter_cost + installation_cost
    }

def calculate_cashflows(params):
    """Calculate annual cash flows and financial metrics"""
    # Get system costs
    costs = calculate_system_cost(params)
    total_system_cost = costs['total_cost']
    
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
    years = list(range(params['analysis_years'] + 1))
    cash_flows = [-total_system_cost]  # Initial investment
    cash_flows.extend([annual_savings] * params['analysis_years'])
    
    # Calculate cumulative NPV for each year
    discount_rate = params['discount_rate'] / 100  # Convert percentage to decimal
    npv_values = []
    running_npv = -total_system_cost
    
    for year in years:
        if year == 0:
            npv_values.append(running_npv)
        else:
            running_npv += annual_savings / ((1 + discount_rate) ** year)
            npv_values.append(running_npv)
    
    # Calculate payback period
    payback_period = None
    for i, npv in enumerate(npv_values):
        if npv >= 0:
            payback_period = i
            break
            
    # Calculate IRR
    try:
        irr = np.roots([total_system_cost] + [-annual_savings] * params['analysis_years'])
        irr = float([r.real for r in irr if r.real > 0 and abs(r.imag) < 1e-10][0]) - 1
    except:
        irr = 0
    
    return {
        'years': years,
        'npv_values': npv_values,
        'annual_savings': annual_savings,
        'system_costs': costs,
        'peak_reduction': actual_peak_reduction,
        'irr': irr,
        'payback_period': payback_period if payback_period is not None else float('inf')
    }

# Page Title
st.title("🔋 SHAVER 🪒")
st.subheader("Storage Harnessing And Value Estimation Return Tool")

# Create three columns for input parameters
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Load Parameters")
    peak_load = st.number_input("Peak Load (kW)", min_value=10, max_value=1000, value=72)
    peak_duration = st.number_input("Peak Duration (hours)", min_value=0.5, max_value=8.0, value=2.5)
    peak_demand_charge = st.number_input("Peak Demand Charge ($/kW)", min_value=5, max_value=50, value=22)

with col2:
    st.subheader("System Parameters")
    battery_power = st.number_input("Battery Power (kW)", min_value=10, max_value=1000, value=60)
    battery_capacity = st.number_input("Battery Capacity (kWh)", min_value=10, max_value=2000, value=210)
    installation_factor = st.number_input("Installation Cost Factor", min_value=0.1, max_value=1.0, value=0.3, help="Additional cost as a fraction of equipment cost")

with col3:
    st.subheader("Cost Parameters")
    battery_cost = st.number_input("Battery Cost ($/kWh)", min_value=100, max_value=1000, value=300)
    inverter_cost = st.number_input("Inverter Cost ($/kW)", min_value=100, max_value=1000, value=200)
    discount_rate = st.number_input("Discount Rate (%)", min_value=0.0, max_value=20.0, value=8.0, step=0.5)
    analysis_years = st.slider("Analysis Period (years)", min_value=5, max_value=30, value=15)

# Collect parameters
params = {
    'peak_load_kw': peak_load,
    'peak_duration_hours': peak_duration,
    'battery_power_kw': battery_power,
    'battery_capacity_kwh': battery_capacity,
    'peak_demand_charge': peak_demand_charge,
    'battery_cost_per_kwh': battery_cost,
    'inverter_cost_per_kw': inverter_cost,
    'installation_factor': installation_factor,
    'discount_rate': discount_rate,
    'analysis_years': analysis_years
}

# Calculate results
results = calculate_cashflows(params)

# Display system costs
st.subheader("System Costs")
cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)

with cost_col1:
    st.metric("Battery Cost", f"${results['system_costs']['battery_cost']:,.0f}")
with cost_col2:
    st.metric("Inverter Cost", f"${results['system_costs']['inverter_cost']:,.0f}")
with cost_col3:
    st.metric("Installation Cost", f"${results['system_costs']['installation_cost']:,.0f}")
with cost_col4:
    st.metric("Total System Cost", f"${results['system_costs']['total_cost']:,.0f}")

# Display performance metrics
st.subheader("Performance Metrics")
metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

with metrics_col1:
    st.metric("Annual Savings", f"${results['annual_savings']:,.0f}")
with metrics_col2:
    st.metric("Peak Reduction", f"{results['peak_reduction']:.1f} kW")
with metrics_col3:
    st.metric("New Peak Value", f"{peak_load - results['peak_reduction']:.1f} kW")

# Display financial metrics
st.subheader("Financial Metrics")
fin_col1, fin_col2, fin_col3 = st.columns(3)

with fin_col1:
    st.metric("Simple Payback", f"{results['payback_period']:.1f} years")
with fin_col2:
    st.metric("IRR", f"{results['irr']*100:.1f}%")
with fin_col3:
    st.metric("Discount Rate", f"{discount_rate:.1f}%")

# Create DataFrame for chart
df = pd.DataFrame({
    'Year': results['years'],
    'NPV': results['npv_values'],
    'Breakeven Line': [0] * len(results['years'])  # Add zero line
})

# Display chart
st.subheader("Project Cash Flows")
st.line_chart(df.set_index('Year'))

# Add breakeven annotation
if results['payback_period'] != float('inf'):
    st.caption(f"⚡ Breakeven occurs at {results['payback_period']:.1f} years")
    st.caption(f"💰 NPV at end of analysis period: ${results['npv_values'][-1]:,.0f}")

# Add explanatory text
st.markdown(f"""
### Analysis Details
- Battery cost: ${battery_cost}/kWh
- Inverter cost: ${inverter_cost}/kW
- Installation factor: {installation_factor*100}% of equipment cost
- Uses {discount_rate}% discount rate for NPV calculations
- Assumes consistent monthly peak demand charges
- Includes 90% round-trip battery efficiency
- All costs and savings are in current dollars
""")
