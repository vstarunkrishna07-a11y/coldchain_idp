import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pydeck as pdk
from datetime import datetime
import time
from engine import init_db, CARGO_PROFILES, calculate_arrhenius_decay, evaluate_status, log_telemetry_entry, get_telemetry_history, clear_db, predict_time_to_breach

init_db()
API_URL = "http://localhost:5000/telemetry"

st.set_page_config(page_title="CryoTrace Enterprise", page_icon="🧊", layout="wide")

st.markdown("""
<style>
    .kpi-card { background: #0f172a; padding: 16px; border-radius: 8px; border-left: 4px solid #3b82f6; box-shadow: 0 4px 6px rgba(0,0,0,0.3); color: white;}
    .kpi-title { font-size: 0.75rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; }
    .kpi-val { font-size: 1.9rem; font-weight: 800; color: #f8fafc; margin-top: 5px; }
    .diagnostic-panel { background: #1e293b; padding: 20px; border-radius: 10px; color: #34d399; font-family: monospace; border: 1px solid #334155;}
</style>
""", unsafe_allow_html=True)

st.title("🧊 CryoTrace Digital Twin & Kinetic Ledger")

tab_dash, tab_twin, tab_map, tab_audit = st.tabs(["📊 Main Dashboard", "🩻 Digital Twin Diagnostics", "🌍 Geospatial", "🔐 Blockchain"])

container_id = st.sidebar.selectbox("Active Transit Unit", ["UNIT-ALPHA-101", "UNIT-BETA-204"])
selected_cargo = st.sidebar.selectbox("Commodity Profile", list(CARGO_PROFILES.keys()))
profile = CARGO_PROFILES[selected_cargo]

state_key = f"state_{container_id}"
if state_key not in st.session_state:
    st.session_state[state_key] = {
        "cargo_type": selected_cargo, "rsl": profile["base_shelf_life_hrs"], "initial_rsl": profile["base_shelf_life_hrs"],
        "cargo_temp": profile["base_temp"], "prev_cargo_temp": profile["base_temp"], "ambient_temp": profile["base_temp"] + 0.5,
        "lat": 12.9692, "lon": 79.1559, "humidity": 40.0, "vibration_g": 1.0, "has_telemetry": False, "last_time": time.time()
    }
c_state = st.session_state[state_key]
prev_temp = c_state["cargo_temp"]

if st.sidebar.button("🔄 System Reset"):
    clear_db()
    st.session_state.clear()
    st.rerun()

try:
    res = requests.get(API_URL, timeout=3)
    live_data = res.json()
    if time.time() - float(live_data.get("last_updated", 0)) < 15:
        c_state.update({"cargo_temp": float(live_data["cargo_temp"]), "ambient_temp": float(live_data["ambient_temp"]), "lat": float(live_data["lat"]), "lon": float(live_data["lon"]), "humidity": float(live_data["humidity"]), "vibration_g": float(live_data.get("vibration_g", 1.0)), "has_telemetry": True})
        st.sidebar.success("🟢 EDGE SENSOR ONLINE")
    else:
        st.sidebar.error("🔴 SENSOR OFFLINE")
except Exception:
    st.sidebar.error("🔴 API DISCONNECTED")

roc = abs(c_state["cargo_temp"] - prev_temp)
c_state["prev_cargo_temp"] = c_state["cargo_temp"]
decay = calculate_arrhenius_decay(c_state["cargo_temp"], profile["base_temp"], profile["ea_factor"], c_state["humidity"], profile["max_humidity"])

if c_state["has_telemetry"]:
    c_state["rsl"] = max(0.0, c_state["rsl"] - (((time.time() - c_state["last_time"]) / 60.0) * decay))
c_state["last_time"] = time.time()

status = evaluate_status(c_state["rsl"], c_state["initial_rsl"], c_state["cargo_temp"], profile["max_safe_temp"], profile["critical_temp"], roc, profile["roc_limit"], c_state["vibration_g"], profile["max_shock_g"], c_state["humidity"], profile["max_humidity"])

if c_state["has_telemetry"]:
    log_telemetry_entry(container_id, selected_cargo, c_state["ambient_temp"], c_state["cargo_temp"], c_state["humidity"], c_state["vibration_g"], roc, decay, c_state["rsl"], c_state["lat"], c_state["lon"], status)

df_hist = get_telemetry_history(container_id)

with tab_dash:
    if "FATAL" in status: st.error(f"🚨 {status}")
    elif "AT-RISK" in status: st.warning(f"⚠️ {status}")
    else: st.success(f"✅ {status}")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-title">Core Temp 🌡️</div><div class="kpi-val">{c_state["cargo_temp"]:.2f}°C</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card" style="border-color:#f59e0b;"><div class="kpi-title">Kinetic Shock 💥</div><div class="kpi-val">{c_state["vibration_g"]:.2f} G</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card" style="border-color:#8b5cf6;"><div class="kpi-title">Decay Multiplier 📈</div><div class="kpi-val">{decay:.2f}x</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card" style="border-color:#10b981;"><div class="kpi-title">Usable Life ⏳</div><div class="kpi-val">{c_state["rsl"]:.1f}h</div></div>', unsafe_allow_html=True)

    if not df_hist.empty:
        ttb = predict_time_to_breach(df_hist, profile['critical_temp'])
        if ttb and ttb != "> 60": st.error(f"🧠 AI PREDICTION: Thermal breach imminent in **~{ttb:.1f} mins**.")

        df_plot = df_hist.iloc[::-1]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['id'], y=df_plot['cargo_temp'], mode='lines', name='Core Temp', line=dict(color='#3b82f6', width=3)))
        fig.add_hline(y=profile['critical_temp'], line_dash="dash", line_color="red")
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

with tab_twin:
    st.markdown("### 🩻 Cargo Structural Integrity & Digital Twin")
    colA, colB = st.columns(2)
    
    with colA:
        st.markdown(f"""
        <div class="diagnostic-panel">
            <b>>> SYS_DIAGNOSTICS_RUNNING</b><br>
            >> PAYLOAD_ID: {container_id}<br>
            >> PROFILE: {selected_cargo}<br>
            >> SHOCK_LIMIT: {profile['max_shock_g']} G<br>
            >> HUMIDITY_LIMIT: {profile['max_humidity']}%<br>
            >> CURRENT_STATE: {status}<br>
            >> AI_TREND_ANALYSIS: ACTIVE
        </div>
        """, unsafe_allow_html=True)

    with colB:
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = c_state["vibration_g"],
            title = {'text': "Kinetic G-Force (Shock)"},
            gauge = {'axis': {'range': [None, 5]},
                     'bar': {'color': "red" if c_state["vibration_g"] > profile['max_shock_g'] else "green"},
                     'steps': [{'range': [0, profile['max_shock_g']], 'color': "lightgray"},
                               {'range': [profile['max_shock_g'], 5], 'color': "salmon"}]}
        ))
        fig_g.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_g, use_container_width=True)

with tab_map:
    if c_state["has_telemetry"]:
        st.pydeck_chart(pdk.Deck(layers=[pdk.Layer('ScatterplotLayer', data=pd.DataFrame({'lat': [c_state["lat"]], 'lon': [c_state["lon"]]}), get_position='[lon, lat]', get_color='[220, 38, 38, 200]', get_radius=100)], initial_view_state=pdk.ViewState(latitude=c_state["lat"], longitude=c_state["lon"], zoom=14, pitch=50), map_style="mapbox://styles/mapbox/dark-v10"))

with tab_audit:
    if not df_hist.empty:
        st.dataframe(df_hist[['timestamp', 'cargo_temp', 'vibration_g', 'humidity', 'status', 'block_hash']].head(10))

time.sleep(1.5)
st.rerun()
