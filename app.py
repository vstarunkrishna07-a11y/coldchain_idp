import streamlit as st
import requests

# Supabase Configuration
SUPABASE_URL = "https://flnbjtkidvzlvjqwpaue.supabase.co/rest/v1/cold_chain_logs?select=*&order=created_at.desc&limit=1"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZsbmJqdGtpZHZ6bHZqcXdwYXVlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg3MDg0NDksImV4cCI6MjEwNDI4NDQ0OX0.RLmFYXNl689yFrxttBE-3x27pHGv85lnKBqr0WGbYyg"

headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}"
}

st.title("Cold Chain Logistics Dashboard")
st.subheader("Live IoT Sensor Stream & Remaining Shelf Life")

def calculate_rsl(temp, delta_t):
    """Calculates dynamic remaining shelf life based on temperature and rate of change."""
    base_rsl = 168.0  # 7 days baseline
    penalty = 0.0
    if temp > 4.0:
        penalty += (temp - 4.0) * 2.0
    if abs(delta_t) > 0.2:
        penalty += abs(delta_t) * 5.0
    return max(0.0, round(base_rsl - penalty, 2))

# Fetch latest data from Supabase database
try:
    response = requests.get(SUPABASE_URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            latest = data[0]
            temp = latest.get("temperature", 4.0)
            humidity = latest.get("humidity", 85.0)
            delta_t = latest.get("delta_t", 0.0)
            
            rsl = calculate_rsl(temp, delta_t)
            
            # Display metrics on the dashboard
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Temperature", f"{temp} °C", f"{delta_t} ΔT")
            col2.metric("Humidity", f"{humidity} %")
            col3.metric("Remaining Shelf Life", f"{rsl} hrs")
            col4.metric("Status", "CRITICAL" if temp > 8.0 or rsl < 24 else "OPTIMAL")
        else:
            st.warning("No data found in Supabase yet. Is your IDLE script running?")
    else:
        st.error(f"Failed to fetch data. Error code: {response.status_code}")
except Exception as e:
    st.error(f"Connection error: {e}")

# Button to manually refresh the view with new database data
if st.button("Refresh Sensor Data"):
    st.rerun()
