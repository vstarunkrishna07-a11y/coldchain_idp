import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time
import random
from engine import (
    init_db, CARGO_PROFILES, calculate_arrhenius_decay,
    evaluate_status, log_telemetry_entry, get_telemetry_history,
    clear_db, generate_pdf_report
)

init_db()

st.set_page_config(
    page_title="ColdChain.AI | Autonomous Telematics",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Polished High-Contrast Modern Theme CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }

    /* Overall Layout Polish */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Top Banner Header */
    .hero-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        border-radius: 16px;
        padding: 24px 30px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #c7d2fe;
        margin: 4px 0 0 0;
    }
    
    /* Metric KPI Cards with Glass Glow */
    .kpi-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 15px -1px rgba(0, 0, 0, 0.05), 0 2px 6px -1px rgba(0, 0, 0, 0.02);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.08);
    }
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .kpi-title {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
    }
    .kpi-icon {
        font-size: 1.2rem;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    .kpi-subtext {
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 4px;
    }

    /* Vibrant Status Alert Banners */
    .status-banner {
        border-radius: 12px;
        padding: 16px 22px;
        margin: 20px 0;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 0.95rem;
    }
    .status-nominal {
        background: linear-gradient(90deg, #ecfdf5 0%, #d1fae5 100%);
        border-left: 6px solid #10b981;
        color: #065f46;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.12);
    }
    .status-warning {
        background: linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 6px solid #f59e0b;
        color: #92400e;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
    }
    .status-danger {
        background: linear-gradient(90deg, #fef2f2 0%, #fee2e2 100%);
        border-left: 6px solid #ef4444;
        color: #991b1b;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
    }

    /* Fleet Cards */
    .fleet-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
    }
</style>
""", unsafe_allow_html=True)

# Top Hero Header
st.markdown("""
<div class="hero-header">
    <div>
        <h1 class="hero-title">❄️ ColdChain.AI <span style="font-size:1rem; font-weight:500; background:#4f46e5; padding:4px 10px; border-radius:20px; margin-left:10px;">ENTERPRISE V2.4</span></h1>
        <p class="hero-subtitle">Autonomous Arrhenius Spoilage Kinetics & Dynamic Telematics Dispatch</p>
    </div>
    <div style="text-align: right;">
        <span style="background: rgba(255,255,255,0.15); padding: 8px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;">🟢 GATEWAY ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_live, tab_fleet = st.tabs(["🚚 Real-Time Shipment Telematics", "🌐 Fleet Overview & Multi-Node Monitor"])

# Sidebar Controls
st.sidebar.markdown("### 🏷️ Cargo Configuration")
container_id = st.sidebar.selectbox("Active Unit", ["CONT-ALPHA-101", "CONT-BETA-204", "CONT-GAMMA-309"])
selected_cargo = st.sidebar.selectbox("Perishable Category", list(CARGO_PROFILES.keys()))
profile = CARGO_PROFILES[selected_cargo]

# Session State Setup
if f"state_{container_id}" not in st.session_state:
    st.session_state[f"state_{container_id}"] = {
        "rsl": profile["base_shelf_life_hrs"],
        "initial_rsl": profile["base_shelf_life_hrs"],
        "cargo_temp": profile["base_temp"],
        "ambient_temp": profile["base_temp"] + 0.5,
        "prev_cargo_temp": profile["base_temp"],
        "is_running": False
    }

c_state = st.session_state[f"state_{container_id}"]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🕹️ Telemetry Engine")
sim_mode = st.sidebar.radio("Mode Selection:", ["Autonomous Telemetry", "Manual Fault Injection"])

if sim_mode == "Autonomous Telemetry":
    c_state["is_running"] = st.sidebar.checkbox("▶️ Run Autonomous Stream", value=True)
    cooling_failure = st.sidebar.checkbox("🚨 Inject Compressor Thermal Leak", value=False)
    
    if cooling_failure:
        target_ambient = profile["critical_temp"] + random.uniform(6.0, 14.0)
    else:
        target_ambient = profile["base_temp"] + random.uniform(-0.4, 0.8)
        
    c_state["ambient_temp"] += (target_ambient - c_state["ambient_temp"]) * 0.35
    humidity = random.uniform(50.0, 60.0) if not cooling_failure else random.uniform(75.0, 88.0)
else:
    c_state["is_running"] = False
    c_state["ambient_temp"] = st.sidebar.slider("Ambient Temp (°C)", float(profile["base_temp"] - 10.0), 40.0, float(c_state["ambient_temp"]), 0.5)
    humidity = st.sidebar.slider("Humidity (%)", 10.0, 95.0, 55.0, 1.0)

if st.sidebar.button("🔄 Reset Shipment Baseline", use_container_width=True):
    c_state["rsl"] = profile["base_shelf_life_hrs"]
    c_state["cargo_temp"] = profile["base_temp"]
    c_state["prev_cargo_temp"] = profile["base_temp"]
    c_state["ambient_temp"] = profile["base_temp"] + 0.5
    clear_db()
    st.rerun()

# Dynamic Physics Calculations
prev_temp = c_state["cargo_temp"]
c_state["cargo_temp"] += (c_state["ambient_temp"] - c_state["cargo_temp"]) * profile["thermal_inertia"]
rate_of_change = abs(c_state["cargo_temp"] - prev_temp)

decay_multiplier = calculate_arrhenius_decay(c_state["cargo_temp"], profile["base_temp"], profile["ea_factor"])
hours_lost = 1.0 * decay_multiplier
c_state["rsl"] = max(0.0, c_state["rsl"] - hours_lost)

status = evaluate_status(
    c_state["rsl"], c_state["initial_rsl"],
    c_state["cargo_temp"], profile["max_safe_temp"],
    profile["critical_temp"], rate_of_change, profile["roc_limit"]
)

# Persist Telemetry
log_telemetry_entry(
    container_id=container_id,
    cargo_type=selected_cargo,
    ambient_temp=round(c_state["ambient_temp"], 2),
    cargo_temp=round(c_state["cargo_temp"], 2),
    humidity=round(humidity, 2),
    roc=round(rate_of_change, 3),
    decay_rate=round(decay_multiplier, 2),
    rsl=round(c_state["rsl"], 2),
    status=status
)

with tab_live:
    # 5 KPI Cards Row
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #2563eb;">
            <div class="kpi-header"><span class="kpi-title">Cargo Core</span><span class="kpi-icon">🌡️</span></div>
            <div class="kpi-value">{c_state["cargo_temp"]:.2f}<span style="font-size:1.1rem; font-weight:500;"> °C</span></div>
            <div class="kpi-subtext" style="color: #2563eb;">Optimal: {profile['base_temp']}°C</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #f59e0b;">
            <div class="kpi-header"><span class="kpi-title">Ambient Sensor</span><span class="kpi-icon">🌤️</span></div>
            <div class="kpi-value">{c_state["ambient_temp"]:.2f}<span style="font-size:1.1rem; font-weight:500;"> °C</span></div>
            <div class="kpi-subtext" style="color: #d97706;">Humidity: {humidity:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m3:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #ec4899;">
            <div class="kpi-header"><span class="kpi-title">Thermal Rate (ΔT)</span><span class="kpi-icon">⚡</span></div>
            <div class="kpi-value">{rate_of_change:.2f}<span style="font-size:1rem; font-weight:500;"> °C/cyc</span></div>
            <div class="kpi-subtext" style="color: #db2777;">Limit: {profile['roc_limit']}°C</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m4:
        decay_color = "#10b981" if decay_multiplier < 1.3 else ("#f59e0b" if decay_multiplier < 3.0 else "#ef4444")
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #8b5cf6;">
            <div class="kpi-header"><span class="kpi-title">Decay Rate</span><span class="kpi-icon">📈</span></div>
            <div class="kpi-value" style="color:{decay_color};">{decay_multiplier:.2f}x</div>
            <div class="kpi-subtext" style="color: #7c3aed;">Arrhenius Factor</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m5:
        rsl_pct = (c_state["rsl"] / c_state["initial_rsl"]) * 100
        rsl_bar_color = "#10b981" if rsl_pct > 50 else ("#f59e0b" if rsl_pct > 20 else "#ef4444")
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid {rsl_bar_color};">
            <div class="kpi-header"><span class="kpi-title">Remaining Life</span><span class="kpi-icon">⏳</span></div>
            <div class="kpi-value">{c_state["rsl"]:.1f}<span style="font-size:1rem; font-weight:500;"> hrs</span></div>
            <div class="kpi-subtext" style="color: {rsl_bar_color};">{rsl_pct:.0f}% capacity remaining</div>
        </div>
        """, unsafe_allow_html=True)

    # Dynamic Triage Banner
    if "NOMINAL" in status:
        st.markdown(f"""<div class="status-banner status-nominal"><span>✅</span> <div><b>SYSTEM STATE: {status}</b><br><span style="font-weight:400; font-size:0.88rem;">Thermal parameters and chemical degradation kinetics are fully within nominal safety margins.</span></div></div>""", unsafe_allow_html=True)
    elif "AT-RISK" in status:
        st.markdown(f"""<div class="status-banner status-warning"><span>⚠️</span> <div><b>SYSTEM STATE: {status}</b><br><span style="font-weight:400; font-size:0.88rem;">Accelerated kinetic degradation detected. Automated action recommended: Trigger depot reroute.</span></div></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="status-banner status-danger"><span>🛑</span> <div><b>SYSTEM STATE: {status}</b><br><span style="font-weight:400; font-size:0.88rem;">Critical temperature threshold permanently breached. Cargo flagged as compromised/spoiled.</span></div></div>""", unsafe_allow_html=True)

    df_hist = get_telemetry_history(container_id)
    if not df_hist.empty:
        df_hist_chrono = df_hist.iloc[::-1]

        col_left, col_right = st.columns(2)
        
        with col_left:
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(
                x=df_hist_chrono['id'], y=df_hist_chrono['cargo_temp'], 
                mode='lines+markers', name='Core Temp', 
                line=dict(color='#2563eb', width=3),
                marker=dict(size=6, color='#1d4ed8')
            ))
            fig_t.add_trace(go.Scatter(
                x=df_hist_chrono['id'], y=df_hist_chrono['ambient_temp'], 
                mode='lines', name='Ambient Sensor', 
                line=dict(dash='dash', color='#94a3b8', width=2)
            ))
            fig_t.add_hline(y=profile['max_safe_temp'], line_dash="dot", line_color="#f59e0b", annotation_text=f"Safe Upper ({profile['max_safe_temp']}°C)", annotation_font_color="#f59e0b")
            fig_t.add_hline(y=profile['critical_temp'], line_dash="solid", line_color="#ef4444", annotation_text=f"Critical ({profile['critical_temp']}°C)", annotation_font_color="#ef4444")
            fig_t.update_layout(
                title=dict(text="<b>Thermal Dynamics & Ingress vs Thresholds</b>", font=dict(size=14, color="#0f172a")),
                height=320, template="plotly_white",
                margin=dict(l=15, r=15, t=40, b=15),
                paper_bgcolor='rgba(255,255,255,1)',
                plot_bgcolor='rgba(248,250,252,0.6)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_t, use_container_width=True)

        with col_right:
            fig_rsl = go.Figure()
            fig_rsl.add_trace(go.Scatter(
                x=df_hist_chrono['id'], y=df_hist_chrono['remaining_shelf_life_hrs'], 
                mode='lines+markers', name='RSL Trajectory', 
                line=dict(color='#10b981', width=3),
                fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.08)',
                marker=dict(size=6, color='#059669')
            ))
            fig_rsl.update_layout(
                title=dict(text="<b>Dynamic Shelf-Life Degradation Curve (RSL)</b>", font=dict(size=14, color="#0f172a")),
                height=320, template="plotly_white",
                margin=dict(l=15, r=15, t=40, b=15),
                paper_bgcolor='rgba(255,255,255,1)',
                plot_bgcolor='rgba(248,250,252,0.6)'
            )
            st.plotly_chart(fig_rsl, use_container_width=True)

        # PDF & Table Audit Section
        st.markdown("### 📋 Regulatory Compliance Audit Trail")
        pdf_bytes = generate_pdf_report(df_hist, container_id, selected_cargo, profile)
        
        c_btn, _ = st.columns([1.5, 3])
        with c_btn:
            current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label="📄 Download Official Compliance Audit (PDF)",
                data=pdf_bytes,
                file_name=f"audit_report_{container_id}_{current_time_str}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.dataframe(
            df_hist[['timestamp', 'container_id', 'cargo_type', 'cargo_temp', 'ambient_temp', 'rate_of_change', 'decay_rate', 'remaining_shelf_life_hrs', 'status']].head(12),
            use_container_width=True
        )

with tab_fleet:
    st.markdown("### 🌐 Active Fleet Units Telematics Summary")
    df_all = get_telemetry_history()
    if not df_all.empty:
        latest_fleet = df_all.groupby('container_id').first().reset_index()
        
        f1, f2, f3 = st.columns(3)
        for idx, row in latest_fleet.iterrows():
            col = [f1, f2, f3][idx % 3]
            with col:
                box_color = "#10b981" if "NOMINAL" in row['status'] else ("#f59e0b" if "AT-RISK" in row['status'] else "#ef4444")
                st.markdown(f"""
                <div class="fleet-card" style="border-top: 5px solid {box_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h3 style="margin:0; font-size:1.15rem; color:#0f172a;">🚛 {row['container_id']}</h3>
                        <span style="background:{box_color}20; color:{box_color}; font-size:0.75rem; font-weight:700; padding:3px 8px; border-radius:12px;">{row['status'][:8]}</span>
                    </div>
                    <p style="margin: 4px 0; font-size: 0.88rem; color: #64748b;">Cargo: <b style="color:#0f172a;">{row['cargo_type']}</b></p>
                    <div style="display: flex; justify-content: space-between; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 8px;">
                        <div>
                            <div style="font-size:0.72rem; color:#64748b; font-weight:600;">CORE TEMP</div>
                            <div style="font-size:1.1rem; font-weight:700; color:#0f172a;">{row['cargo_temp']:.2f} °C</div>
                        </div>
                        <div>
                            <div style="font-size:0.72rem; color:#64748b; font-weight:600;">REMAINING LIFE</div>
                            <div style="font-size:1.1rem; font-weight:700; color:#0f172a;">{row['remaining_shelf_life_hrs']:.1f} hrs</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("---")
        st.dataframe(df_all[['timestamp', 'container_id', 'cargo_type', 'cargo_temp', 'ambient_temp', 'remaining_shelf_life_hrs', 'status']], use_container_width=True)
    else:
        st.info("No active fleet telemetry captured yet.")

if c_state["is_running"]:
    time.sleep(1.8)
    st.rerun()