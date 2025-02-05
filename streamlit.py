import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
            
    # Calculate IRR (simple approximation)
    try:
        irr = np.roots([total_system_cost] + [-annual_savings] * params['analysis_years'])
        irr = float([r.real for r in irr if r.real > 0 and abs(r.imag) < 1e-10][0]) - 1
    except:
        irr = 0
    
    return {
        'years': years,
        'npv_values': npv_values,
        'annual_savings': annual_savings,
        'total_system_cost': total_system_cost,
        'peak_reduction': actual_peak_reduction,
        'irr': irr,
        'payback_period': payback_period if payback_period is not None else float('inf')
    }

# Page Title
st.title("Battery Storage Peak Shaving Analysis")

# Create two columns for input parameters
col1, col2 = st.columns(2)

with col1:
    st.subheader("System Parameters")
    peak_load = st.number_input("Peak Load (kW)", min_value=10, max_value=1000, value=72)
    peak_duration = st.number_input("Peak Duration (hours)", min_value=0.5, max_value=8.0, value=2.5)
    battery_power = st.number_input("Battery Power (kW)", min_value=10, max_value=1000, value=60)
    battery_capacity = st.number_input("Battery Capacity (kWh)", min_value=10, max_value=2000, value=210)

with col2:
    st.subheader("Financial Parameters")
    peak_demand_charge = st.number_input("Peak Demand Charge ($/kW)", min_value=5, max_value=50, value=22)
    system_cost = st.number_input("System Cost ($/kWh)", min_value=100, max_value=1000, value=426)
    discount_rate = st.number_input("Discount Rate (%)", min_value=0.0, max_value=20.0, value=8.0, step=0.5)
    analysis_years = st.slider("Analysis Period (years)", min_value=5, max_value=30, value=15)

# Collect parameters
params = {
    'peak_load_kw': peak_load,
    'peak_duration_hours': peak_duration,
    'battery_power_kw': battery_power,
    'battery_capacity_kwh': battery_capacity,
    'peak_demand_charge': peak_demand_charge,
    'system_cost_per_kwh': system_cost,
    'discount_rate': discount_rate,
    'analysis_years': analysis_years
}

# Calculate results
results = calculate_cashflows(params)

# Display key metrics
st.subheader("Key Metrics")
metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

with metrics_col1:
    st.metric("Total System Cost", f"${results['total_system_cost']:,.0f}")
with metrics_col2:
    st.metric("Annual Savings", f"${results['annual_savings']:,.0f}")
with metrics_col3:
    st.metric("Peak Reduction", f"{results['peak_reduction']:.1f} kW")

metrics_col4, metrics_col5, metrics_col6 = st.columns(3)
with metrics_col4:
    st.metric("Simple Payback", f"{results['payback_period']:.1f} years")
with metrics_col5:
    st.metric("IRR", f"{results['irr']*100:.1f}%")
with metrics_col6:
    st.metric("Discount Rate", f"{discount_rate:.1f}%")

# Create matplotlib figure
fig, ax = plt.subplots(figsize=(10, 6))

# Plot NPV line
ax.plot(results['years'], results['npv_values'], marker='o', linewidth=2, color='blue')

# Add value labels
for i, npv in enumerate(results['npv_values']):
    if i % 2 == 0:  # Label every other point to avoid crowding
        ax.annotate(f'${npv/1000:.1f}k', 
                   (results['years'][i], npv),
                   textcoords="offset points",
                   xytext=(0,10),
                   ha='center')

# Add payback period line and callout
if results['payback_period'] != float('inf'):
    # Vertical line at breakeven
    ax.axvline(x=results['payback_period'], color='red', linestyle='--', alpha=0.7, linewidth=2)
    
    # Calculate y-position for annotation (midpoint of chart)
    y_range = max(results['npv_values']) - min(results['npv_values'])
    y_mid = min(results['npv_values']) + y_range/2
    
    # Add callout annotation
    ax.annotate(f'Breakeven: {results["payback_period"]:.1f} years',
                xy=(results['payback_period'], 0),
                xytext=(results['payback_period'] + 1, y_mid),
                ha='left',
                va='center',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0',
                               color='red', alpha=0.7))

# Add zero line
ax.axhline(y=0, color='gray', linestyle=':')

# Customize plot
ax.set_title('Project Cash Flows')
ax.set_xlabel('Year')
ax.set_ylabel('Net Present Value ($)')
ax.grid(True)

# Display the plot
st.pyplot(fig)

# Add explanatory text
st.markdown(f"""
### Analysis Details
- The model calculates both power-limited and energy-limited peak reduction
- Uses {discount_rate}% discount rate for NPV calculations
- Assumes consistent monthly peak demand charges
- Includes 90% round-trip battery efficiency
- All costs and savings are in current dollars
""")
