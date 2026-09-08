import streamlit as st
import requests
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
API_URL = "https://richard-supposed-pioneer-root.trycloudflare.com/telemetry"

st.set_page_config(
    page_title="CryoTrace Enterprise | Telematics Gateway",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enterprise Engineering Design System CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    code, .stCode {
        font-family: 'JetBrains Mono', monospace;
    }

    .stApp {
        background-color: #f8fafc;
    }
    
    /* Top Corporate Header */
    .hero-header {
        background: linear-gradient(135deg, #091e42 0%, #0c2b5f 50%, #173b7a 100%);
        border-radius: 14px;
        padding: 22px 28px;
        color: #ffffff;
        margin-bottom: 22px;
        box-shadow: 0 10px 20px -5px rgba(9, 30, 66, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .hero-title {
        font-size: 1.65rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .hero-badge {
        font-size: 0.72rem;
        font-weight: 700;
        background: #2563eb;
        color: #ffffff;
        padding: 3px 10px;
        border-radius: 6px;
        letter-spacing: 0.05em;
    }
    .hero-subtitle {
        font-size: 0.9rem;
        color: #93c5fd;
        margin: 4px 0 0 0;
    }
    
    /* Sidebar Section Cards */
    .sidebar-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    /* KPI Metric Cards */
    .kpi-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid #e2e8f0;
        border-top-width: 4px;
        transition: transform 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
    }
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .kpi-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .kpi-subtext {
        font-size: 0.78rem;
        font-weight: 600;
        margin-top: 4px;
    }

    /* Status Banners */
    .status-banner {
        border-radius: 10px;
        padding: 14px 20px;
        margin: 18px 0;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 0.92rem;
    }
    .status-nominal {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-left: 5px solid #10b981;
        color: #065f46;
    }
    .status-warning {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-left: 5px solid #f59e0b;
        color: #92400e;
    }
    .status-danger {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 5px solid #ef4444;
        color: #991b1b;
    }

    /* Fleet Cards */
    .fleet-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #2563eb;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
</style>
""", unsafe_allow_html=True)

# Main Title Header
st.markdown("""
<div class="hero-header">
    <div>
        <h1 class="hero-title">
            🧊 CryoTrace Enterprise
            <span class="hero-badge">TELEMATICS GATEWAY</span>
        </h1>
        <p class="hero-subtitle">Arrhenius Reaction Kinetics & Multi-Cargo Thermodynamic Integrity Engine</p>
    </div>
    <div style="text-align: right;">
        <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #34d399; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.05em;">● TELEMETRY STREAM ONLINE</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_live, tab_fleet = st.tabs(["🚚 Real-Time Shipment Telematics", "🌐 Multi-Unit Fleet Operations"])

# Sidebar - Structured Configuration Panels
st.sidebar.markdown("""
<div class="sidebar-section-title">📦 Shipment Identifier & Cargo</div>
""", unsafe_allow_html=True)

container_id = st.sidebar.selectbox("Active Transit Unit", ["UNIT-ALPHA-101", "UNIT-BETA-204", "UNIT-GAMMA-309"], label_visibility="collapsed")
selected_cargo = st.sidebar.selectbox("Perishable Commodity Profile", list(CARGO_PROFILES.keys()))
profile = CARGO_PROFILES[selected_cargo]

# Session State Setup
if f"state_{container_id}" not in st.session_state:
    st.session_state[f"state_{container_id}"] = {
        "rsl": profile["base_shelf_life_hrs"],
        "initial_rsl": profile["base_shelf_life_hrs"],
        "cargo_temp": profile["base_temp"],
        "ambient_temp": profile["base_temp"] + 0.5,
        "prev_cargo_temp": profile["base_temp"],
        "humidity": 35.0,
        "last_decay_time": time.time(),
        "is_running": False
    }

c_state = st.session_state[f"state_{container_id}"]

# Sidebar - Thermodynamic Threshold Reference Card
st.sidebar.markdown(f"""
<div class="sidebar-card">
    <div class="sidebar-section-title">📋 Kinetic Specification Baseline</div>
    <div style="font-size: 0.8rem; color: #475569; display: grid; gap: 4px;">
        <div>• <b>Baseline Storage:</b> <code>{profile['base_temp']} °C</code></div>
        <div>• <b>Safe Threshold:</b> <code>{profile['max_safe_temp']} °C</code></div>
        <div>• <b>Critical Ingress Limit:</b> <code>{profile['critical_temp']} °C</code></div>
        <div>• <b>Initial Shelf Life:</b> <code>{profile['base_shelf_life_hrs']} hrs</code></div>
        <div>• <b>RoC Rate Limit:</b> <code>{profile['roc_limit']} °C/cyc</code></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar - Live ESP32 Telemetry
st.sidebar.markdown("""
<div class="sidebar-section-title">📡 Live ESP32 Telemetry</div>
""", unsafe_allow_html=True)

# Keep the previous sensor reading so Rate of Change can be calculated
prev_temp = c_state["cargo_temp"]

# Remember last successfully received telemetry inside this Streamlit session
if "last_good_telemetry" not in st.session_state:
    st.session_state["last_good_telemetry"] = None

# Use the last valid humidity instead of forcing 0% during connection failures
humidity = c_state.get("humidity", 35.0)
cooling_failure = False

try:
    response = requests.get(API_URL, timeout=5)
    response.raise_for_status()
    live_data = response.json()

    last_updated = live_data.get("last_updated")

    # Check whether ESP32 data itself is fresh
    if last_updated is not None:
        telemetry_age = time.time() - float(last_updated)
    else:
        telemetry_age = float("inf")

    if telemetry_age <= 15:

        c_state["cargo_temp"] = float(live_data["cargo_temp"])
        c_state["ambient_temp"] = float(live_data["ambient_temp"])

        # Save the latest real humidity reading
        humidity = float(live_data["humidity"])
        c_state["humidity"] = humidity

        cooling_failure = bool(
            live_data.get("compressor_failure", False)
        )

        st.session_state["last_good_telemetry"] = time.time()
        c_state["is_running"] = True

        st.sidebar.success("🟢 ESP32 TELEMETRY ONLINE")
        st.sidebar.caption(
            f"Shipment: {live_data.get('shipment_id', 'UNKNOWN')}"
        )

        if cooling_failure:
            st.sidebar.error(
                "⚠️ COMPRESSOR FAILURE SIGNAL ACTIVE"
            )

    else:
        # API works, but ESP32 has stopped sending fresh readings.
        # Keep the last valid humidity instead of replacing it with 0%.
        humidity = c_state.get("humidity", 35.0)
        cooling_failure = False
        c_state["is_running"] = False

        st.sidebar.error("🔴 ESP32 TELEMETRY OFFLINE")
        st.sidebar.caption(
            "No fresh telemetry received from ESP32."
        )

except Exception:

    # A single temporary Cloudflare/API failure should NOT
    # immediately declare the ESP32 offline.
    last_good = st.session_state["last_good_telemetry"]

    if (
        last_good is not None
        and time.time() - last_good <= 15
    ):
        c_state["is_running"] = True
        humidity = c_state.get("humidity", 35.0)
        cooling_failure = False

        st.sidebar.warning(
            "🟡 TELEMETRY CONNECTION UNSTABLE"
        )
        st.sidebar.caption(
            "Temporary API interruption — using last valid sensor values."
        )

    else:
        c_state["is_running"] = False
        humidity = c_state.get("humidity", 35.0)
        cooling_failure = False

        st.sidebar.error(
            "🔴 ESP32 TELEMETRY OFFLINE"
        )
        st.sidebar.caption(
            "Telemetry connection unavailable. Last valid sensor values retained."
        )
# Optional baseline reset
st.sidebar.write("")
if st.sidebar.button("🔄 Reset Thermodynamic Baseline", use_container_width=True):
    c_state["rsl"] = profile["base_shelf_life_hrs"]
    c_state["cargo_temp"] = profile["base_temp"]
    c_state["prev_cargo_temp"] = profile["base_temp"]
    c_state["ambient_temp"] = profile["base_temp"] + 0.5
    c_state["humidity"] = 35.0
    c_state["last_decay_time"] = time.time()
    clear_db()
    st.rerun()

# Live Sensor Calculations
rate_of_change = abs(c_state["cargo_temp"] - prev_temp)
c_state["prev_cargo_temp"] = c_state["cargo_temp"]

decay_multiplier = calculate_arrhenius_decay(
    c_state["cargo_temp"],
    profile["base_temp"],
    profile["ea_factor"]
)

# Demo-time shelf-life progression.
# 1 real minute = 1 simulated hour.
# This keeps the RSL visibly moving during the presentation without
# destroying the whole shelf life in a few seconds.
current_time = time.time()
last_decay_time = c_state.get("last_decay_time", current_time)
elapsed_seconds = max(0.0, current_time - last_decay_time)
c_state["last_decay_time"] = current_time

simulated_hours = elapsed_seconds / 60.0
hours_lost = simulated_hours * decay_multiplier
c_state["rsl"] = max(0.0, c_state["rsl"] - hours_lost)

status = evaluate_status(
    c_state["rsl"], c_state["initial_rsl"],
    c_state["cargo_temp"], profile["max_safe_temp"],
    profile["critical_temp"], rate_of_change, profile["roc_limit"]
)

# A hardware compressor-failure signal must be reflected in the dashboard state
if cooling_failure and "COMPROMISED" not in status:
    status = "AT-RISK (Compressor Failure)"

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
    # 5 Key Engineering Metric Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #2563eb;">
            <div class="kpi-header"><span class="kpi-title">Cargo Core Temp</span><span>🌡️</span></div>
            <div class="kpi-value">{c_state["cargo_temp"]:.2f}<span style="font-size:1rem; font-weight:500;"> °C</span></div>
            <div class="kpi-subtext" style="color: #2563eb;">Baseline: {profile['base_temp']}°C</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #f59e0b;">
            <div class="kpi-header"><span class="kpi-title">Ambient Sensor</span><span>🌤️</span></div>
            <div class="kpi-value">{c_state["ambient_temp"]:.2f}<span style="font-size:1rem; font-weight:500;"> °C</span></div>
            <div class="kpi-subtext" style="color: #d97706;">Humidity: {humidity:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m3:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #ec4899;">
            <div class="kpi-header"><span class="kpi-title">Rate of Change (ΔT)</span><span>⚡</span></div>
            <div class="kpi-value">{rate_of_change:.2f}<span style="font-size:0.9rem; font-weight:500;"> °C/cyc</span></div>
            <div class="kpi-subtext" style="color: #db2777;">Limit: {profile['roc_limit']}°C</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m4:
        decay_color = "#10b981" if decay_multiplier < 1.3 else ("#f59e0b" if decay_multiplier < 3.0 else "#ef4444")
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #8b5cf6;">
            <div class="kpi-header"><span class="kpi-title">Arrhenius Decay</span><span>📈</span></div>
            <div class="kpi-value" style="color:{decay_color};">{decay_multiplier:.2f}x</div>
            <div class="kpi-subtext" style="color: #7c3aed;">Kinetic Multiplier</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m5:
        rsl_pct = (c_state["rsl"] / c_state["initial_rsl"]) * 100
        rsl_bar_color = "#10b981" if rsl_pct > 50 else ("#f59e0b" if rsl_pct > 20 else "#ef4444")
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: {rsl_bar_color};">
            <div class="kpi-header"><span class="kpi-title">Remaining Life</span><span>⏳</span></div>
            <div class="kpi-value">{c_state["rsl"]:.1f}<span style="font-size:0.95rem; font-weight:500;"> hrs</span></div>
            <div class="kpi-subtext" style="color: {rsl_bar_color};">{rsl_pct:.0f}% margin usable</div>
        </div>
        """, unsafe_allow_html=True)

    # Dynamic Triage Banner
    if "NOMINAL" in status:
        st.markdown(f"""<div class="status-banner status-nominal"><span>✅</span> <div><b>SYSTEM STATUS: {status}</b><br><span style="font-weight:400; font-size:0.86rem;">Thermal equilibrium within nominal range. Arrhenius reaction rates are within validated safety parameters.</span></div></div>""", unsafe_allow_html=True)
    elif "AT-RISK" in status:
        st.markdown(f"""<div class="status-banner status-warning"><span>⚠️</span> <div><b>SYSTEM STATUS: {status}</b><br><span style="font-weight:400; font-size:0.86rem;">Thermal excursion detected. Kinetic decay is accelerated. Automated action: Initiate logistics reroute protocol.</span></div></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="status-banner status-danger"><span>🛑</span> <div><b>SYSTEM STATUS: {status}</b><br><span style="font-weight:400; font-size:0.86rem;">Critical temperature threshold breached. Cumulative thermal damage exceeds regulatory specifications. Cargo flagged unusable.</span></div></div>""", unsafe_allow_html=True)

    df_hist = get_telemetry_history(container_id)
    if not df_hist.empty:
        df_hist_chrono = df_hist.iloc[::-1]

        col_left, col_right = st.columns(2)
        
        with col_left:
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(
                x=df_hist_chrono['id'], y=df_hist_chrono['cargo_temp'], 
                mode='lines+markers', name='Core Temp', 
                line=dict(color='#2563eb', width=2.5),
                marker=dict(size=5, color='#1d4ed8')
            ))
            fig_t.add_trace(go.Scatter(
                x=df_hist_chrono['id'], y=df_hist_chrono['ambient_temp'], 
                mode='lines', name='Ambient Sensor', 
                line=dict(dash='dash', color='#94a3b8', width=1.5)
            ))
            fig_t.add_hline(y=profile['max_safe_temp'], line_dash="dot", line_color="#f59e0b", annotation_text=f"Safe Upper ({profile['max_safe_temp']}°C)", annotation_font_color="#f59e0b")
            fig_t.add_hline(y=profile['critical_temp'], line_dash="solid", line_color="#ef4444", annotation_text=f"Critical Limit ({profile['critical_temp']}°C)", annotation_font_color="#ef4444")
            fig_t.update_layout(
                title=dict(text="<b>Thermal Dynamics & Ingress vs Validated Limits</b>", font=dict(size=13, color="#0f172a")),
                height=310, template="plotly_white",
                margin=dict(l=15, r=15, t=35, b=15),
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
                line=dict(color='#059669', width=2.5),
                fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.08)',
                marker=dict(size=5, color='#047857')
            ))
            fig_rsl.update_layout(
                title=dict(text="<b>Dynamic Shelf-Life Degradation Trajectory (RSL)</b>", font=dict(size=13, color="#0f172a")),
                height=310, template="plotly_white",
                margin=dict(l=15, r=15, t=35, b=15),
                paper_bgcolor='rgba(255,255,255,1)',
                plot_bgcolor='rgba(248,250,252,0.6)'
            )
            st.plotly_chart(fig_rsl, use_container_width=True)

        # PDF & Table Audit Section
        st.markdown("### 📋 Regulatory Compliance & Cryptographic Audit Trail")
        pdf_bytes = generate_pdf_report(df_hist, container_id, selected_cargo, profile)
        
        c_btn, _ = st.columns([1.5, 3])
        with c_btn:
            current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label="📄 Export Compliance Audit Certificate (PDF)",
                data=pdf_bytes,
                file_name=f"cryotrace_audit_{container_id}_{current_time_str}.pdf",
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
                <div class="fleet-card" style="border-top-color: {box_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h3 style="margin:0; font-size:1.1rem; color:#0f172a;">🚛 {row['container_id']}</h3>
                        <span style="background:{box_color}18; color:{box_color}; font-size:0.75rem; font-weight:700; padding:3px 8px; border-radius:6px;">{row['status'][:8]}</span>
                    </div>
                    <p style="margin: 4px 0; font-size: 0.85rem; color: #64748b;">Commodity: <b style="color:#0f172a;">{row['cargo_type']}</b></p>
                    <div style="display: flex; justify-content: space-between; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #f1f5f9;">
                        <div>
                            <div style="font-size:0.7rem; color:#64748b; font-weight:600;">CORE TEMP</div>
                            <div style="font-size:1.05rem; font-weight:700; color:#0f172a;">{row['cargo_temp']:.2f} °C</div>
                        </div>
                        <div>
                            <div style="font-size:0.7rem; color:#64748b; font-weight:600;">USABLE MARGIN</div>
                            <div style="font-size:1.05rem; font-weight:700; color:#0f172a;">{row['remaining_shelf_life_hrs']:.1f} hrs</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("---")
        st.dataframe(df_all[['timestamp', 'container_id', 'cargo_type', 'cargo_temp', 'ambient_temp', 'remaining_shelf_life_hrs', 'status']], use_container_width=True)
    else:
        st.info("No active fleet units recorded yet.")

time.sleep(1.8)
st.rerun()
