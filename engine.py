import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime
import hashlib
from sklearn.linear_model import LinearRegression

DB_NAME = "coldchain_telemetry.db"

CARGO_PROFILES = {
    "mRNA Vaccines (Ultra-Cold)": {
        "base_temp": -20.0, "max_safe_temp": -15.0, "critical_temp": -5.0,
        "base_shelf_life_hrs": 72.0, "ea_factor": 0.12, "roc_limit": 1.5,
        "max_shock_g": 2.5, "max_humidity": 50.0
    },
    "Insulin / Biologics": {
        "base_temp": 4.0, "max_safe_temp": 8.0, "critical_temp": 15.0,
        "base_shelf_life_hrs": 720.0, "ea_factor": 0.09, "roc_limit": 1.0,
        "max_shock_g": 3.0, "max_humidity": 65.0
    },
    "High-Value Electronics (Silicon)": {
        "base_temp": 20.0, "max_safe_temp": 30.0, "critical_temp": 45.0,
        "base_shelf_life_hrs": 2000.0, "ea_factor": 0.02, "roc_limit": 5.0,
        "max_shock_g": 1.8, "max_humidity": 40.0
    }
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Dropping old table to update the schema with vibration_g
    cursor.execute("DROP TABLE IF EXISTS telemetry")
    cursor.execute("""
        CREATE TABLE telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, container_id TEXT, cargo_type TEXT,
            ambient_temp REAL, cargo_temp REAL, humidity REAL, vibration_g REAL,
            rate_of_change REAL, decay_rate REAL, remaining_shelf_life_hrs REAL,
            lat REAL, lon REAL, status TEXT, prev_hash TEXT, block_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

def generate_block_hash(prev_hash, timestamp, container_id, temp, rsl):
    payload = f"{prev_hash}{timestamp}{container_id}{temp:.2f}{rsl:.2f}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def get_last_hash(container_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT block_hash FROM telemetry WHERE container_id = ? ORDER BY id DESC LIMIT 1", (container_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"

def calculate_arrhenius_decay(temp_celsius, base_temp, ea_factor, humidity, max_humidity):
    temp_diff = max(0.0, temp_celsius - base_temp)
    # Humidity above threshold accelerates chemical decay by 20%
    humidity_penalty = 1.2 if humidity > max_humidity else 1.0
    return float(np.exp(ea_factor * temp_diff)) * humidity_penalty

def evaluate_status(remaining_rsl, initial_rsl, temp, max_safe_temp, critical_temp, roc, roc_limit, shock_g, max_shock, humidity, max_hum):
    if shock_g > max_shock:
        return "FATAL: STRUCTURAL SHOCK (CARGO DESTROYED)"
    if temp >= critical_temp:
        return "FATAL: THERMAL BREACH (DISCARD)"
    if humidity > (max_hum * 1.2):
        return "AT-RISK: MOISTURE INGRESS"
    if remaining_rsl < (initial_rsl * 0.4) or temp > max_safe_temp or roc > roc_limit:
        return "AT-RISK: THERMAL DEGRADATION"
    return "NOMINAL: SYSTEM STABLE"

def log_telemetry_entry(cid, ctype, atemp, ctemp, hum, vib, roc, decay, rsl, lat, lon, stat):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    phash = get_last_hash(cid)
    bhash = generate_block_hash(phash, ts, cid, ctemp, rsl)
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO telemetry (timestamp, container_id, cargo_type, ambient_temp, cargo_temp, humidity, vibration_g, rate_of_change, decay_rate, remaining_shelf_life_hrs, lat, lon, status, prev_hash, block_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                 (ts, cid, ctype, atemp, ctemp, hum, vib, roc, decay, rsl, lat, lon, stat, phash, bhash))
    conn.commit()
    conn.close()

def get_telemetry_history(container_id=None):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM telemetry {'WHERE container_id = ?' if container_id else ''} ORDER BY id DESC LIMIT 50", conn, params=(container_id,) if container_id else ())
    conn.close()
    return df

def clear_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM telemetry")
    conn.commit()
    conn.close()

def predict_time_to_breach(df_hist, critical_temp):
    if len(df_hist) < 5: return None
    recent = df_hist.head(10).iloc[::-1].reset_index()
    X = np.array(recent.index).reshape(-1, 1)
    y = np.array(recent['cargo_temp'])
    model = LinearRegression().fit(X, y)
    if model.coef_[0] <= 0.05: return "> 60"
    minutes = ((critical_temp - y[-1]) / model.coef_[0]) * (5/60)
    return max(0, minutes)
