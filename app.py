import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pydeck as pdk
from datetime import datetime
import time
from engine import (
    init_db, CARGO_PROFILES, calculate_arrhenius_decay,
    evaluate_status, log_telemetry_entry, get_telemetry_history,
    clear_db, predict_time_to_breach
)

init_db()
API_URL = "http://localhost:5000/telemetry" # Update this to your Ngrok/Cloudflare URL for Wokwi

st.set_page_config(page_title="CryoTrace Enterprise", page_icon="🧊", layout="wide", initial_sidebar_state="expanded")

# Enterprise CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    code { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
    .hero-header { background: linear-gradient(135deg, #020617 0%, #0f172a 100%); padding: 22px 28px; color: white; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .kpi-card { background: white; padding: 16px; border-radius: 10px; border: 1px solid #e2e8f0; border-top: 4px solid #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-title { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-val { font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-top: 5px; }
    .hash-box { background: #f8fafc; border: 1px dashed #cbd5e1; padding: 10px; border-radius: 6px; font-size: 0.75rem; word-break: break-all; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-header">
    <div>
        <h1 style="margin:0; font-size:1.8rem; font-weight:800;">🧊 CryoTrace Enterprise</h1>
        <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.9rem;">Cyber-Physical Telematics & Cryptographic Supply Chain Ledger</p>
    </div>
    <div>
        <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #10b981; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 0.8rem;">● SECURE GATEWAY ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_live, tab_map, tab_audit = st.tabs(["🚚 Real-Time Telematics", "🌍 Geospatial Tracking", "🔐 Cryptographic Ledger"])

# Sidebar Logic
container_id = st.sidebar.selectbox("Active Transit Unit", ["UNIT-ALPHA-101", "UNIT-BETA-204"])
selected_cargo = st.sidebar.selectbox("Commodity Profile", list(CARGO_PROFILES.keys()))
profile = CARGO_PROFILES[selected_cargo]

state_key = f"state_{container_id}"
if state_key not in st.session_state:
    st.session_state[state_key] = {
        "cargo_type": selected_cargo, "rsl": profile["base_shelf_life_hrs"], "initial_rsl": profile["base_shelf_life_hrs"],
        "cargo_temp": profile["base_temp"], "prev_cargo_temp": profile["base_temp"], "ambient_temp": profile["base_temp"] + 0.5,
        "lat": 12.9692, "lon": 79.1559, "humidity": 40.0, "has_telemetry": False, "last_time": time.time()
    }

c_state = st.session_state[state_key]
prev_temp = c_state["cargo_temp"]

# Fetch Telemetry
try:
    res = requests.get(API_URL, timeout=3)
    res.raise_for_status()
    live_data = res.json()
    
    if time.time() - float(live_data.get("last_updated", 0)) < 30:
        c_state["cargo_temp"] = float(live_data["cargo_temp"])
        c_state["ambient_temp"] = float(live_data["ambient_temp"])
        c_state["lat"] = float(live_data["lat"])
        c_state["lon"] = float(live_data["lon"])
        c_state["has_telemetry"] = True
        st.sidebar.success("🟢 EDGE SENSOR ONLINE")
    else:
        st.sidebar.error("🔴 SENSOR OFFLINE (Using Cached Data)")
except Exception:
    st.sidebar.error("🔴 API DISCONNECTED")

if st.sidebar.button("🔄 Reset Environment", use_container_width=True):
    clear_db()
    st.session_state.clear()
    st.rerun()

# Calculations
rate_of_change = abs(c_state["cargo_temp"] - prev_temp)
c_state["prev_cargo_temp"] = c_state["cargo_temp"]
decay = calculate_arrhenius_decay(c_state["cargo_temp"], profile["base_temp"], profile["ea_factor"])

if c_state["has_telemetry"]:
    elapsed = (time.time() - c_state["last_time"]) / 60.0
    c_state["rsl"] = max(0.0, c_state["rsl"] - (elapsed * decay))
c_state["last_time"] = time.time()

status = evaluate_status(c_state["rsl"], c_state["initial_rsl"], c_state["cargo_temp"], profile["max_safe_temp"], profile["critical_temp"], rate_of_change, profile["roc_limit"])

if c_state["has_telemetry"]:
    log_telemetry_entry(container_id, selected_cargo, c_state["ambient_temp"], c_state["cargo_temp"], c_state["humidity"], rate_of_change, decay, c_state["rsl"], c_state["lat"], c_state["lon"], status)

df_hist = get_telemetry_history(container_id)

with tab_live:
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="kpi-card"><div class="kpi-title">Core Temp 🌡️</div><div class="kpi-val">{c_state["cargo_temp"]:.2f}°C</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="kpi-card" style="border-color:#f59e0b;"><div class="kpi-title">Ambient 🌤️</div><div class="kpi-val">{c_state["ambient_temp"]:.2f}°C</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="kpi-card" style="border-color:#8b5cf6;"><div class="kpi-title">Kinetic Decay 📈</div><div class="kpi-val">{decay:.2f}x</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="kpi-card" style="border-color:#10b981;"><div class="kpi-title">Usable Life ⏳</div><div class="kpi-val">{c_state["rsl"]:.1f}h</div></div>', unsafe_allow_html=True)

    if not df_hist.empty:
        # ML Predictive Alert
        ttb = predict_time_to_breach(df_hist, profile['critical_temp'])
        if ttb and ttb != "> 60":
            st.error(f"🧠 **AI PREDICTIVE ALERT:** Based on current thermal trajectory, critical failure is imminent in **~{ttb:.1f} minutes**. Recommend immediate logistical reroute.")

        # Plotly Chart
        df_plot = df_hist.iloc[::-1]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['id'], y=df_plot['cargo_temp'], mode='lines', name='Core Temp', line=dict(color='#3b82f6', width=3)))
        fig.add_hline(y=profile['critical_temp'], line_dash="dash", line_color="red", annotation_text="CRITICAL LIMIT")
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

with tab_map:
    st.markdown("### 🛰️ Live Geospatial Telemetry")
    if c_state["has_telemetry"]:
        # PyDeck 3D Map configured near VIT
        map_data = pd.DataFrame({'lat': [c_state["lat"]], 'lon': [c_state["lon"]]})
        view_state = pdk.ViewState(latitude=c_state["lat"], longitude=c_state["lon"], zoom=14, pitch=50)
        layer = pdk.Layer(
            'ScatterplotLayer', data=map_data, get_position='[lon, lat]',
            get_color='[220, 38, 38, 200]', get_radius=100, pickable=True
        )
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/light-v9"))
        st.caption(f"Current Coordinates: {c_state['lat']}, {c_state['lon']}")

with tab_audit:
    st.markdown("### 🔐 Cryptographic Immutable Ledger")
    st.info("Every telemetry entry is hashed with the SHA-256 signature of the previous entry, establishing a tamper-proof chain of custody for pharmaceutical compliance (CFR Part 11).")
    
    if not df_hist.empty:
        for idx, row in df_hist.head(5).iterrows():
            st.markdown(f"""
            <div class="hash-box">
                <b>Block ID:</b> {row['id']} | <b>Time:</b> {row['timestamp']} | <b>Temp:</b> {row['cargo_temp']}°C<br>
                <span style="color:#64748b;">Previous Hash:</span> <code>{row['prev_hash']}</code><br>
                <span style="color:#0f172a;"><b>Block Hash:</b></span> <code>{row['block_hash']}</code>
            </div>
            """, unsafe_allow_html=True)

time.sleep(2)
st.rerun()
