import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import hashlib
from sklearn.linear_model import LinearRegression

DB_NAME = "coldchain_telemetry.db"

CARGO_PROFILES = {
    "mRNA Vaccines (Ultra-Cold)": {
        "base_temp": -20.0, "max_safe_temp": -15.0, "critical_temp": -5.0,
        "base_shelf_life_hrs": 72.0, "ea_factor": 0.12, "roc_limit": 1.5
    },
    "Insulin / Biologics": {
        "base_temp": 4.0, "max_safe_temp": 8.0, "critical_temp": 15.0,
        "base_shelf_life_hrs": 720.0, "ea_factor": 0.09, "roc_limit": 1.0
    },
    "Fresh Seafood / Meat": {
        "base_temp": 0.0, "max_safe_temp": 4.0, "critical_temp": 10.0,
        "base_shelf_life_hrs": 48.0, "ea_factor": 0.14, "roc_limit": 1.0
    }
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            container_id TEXT,
            cargo_type TEXT,
            ambient_temp REAL,
            cargo_temp REAL,
            humidity REAL,
            rate_of_change REAL,
            decay_rate REAL,
            remaining_shelf_life_hrs REAL,
            lat REAL,
            lon REAL,
            status TEXT,
            prev_hash TEXT,
            block_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

def generate_block_hash(prev_hash, timestamp, container_id, temp, rsl):
    """Generates a SHA-256 hash for immutable auditing."""
    payload = f"{prev_hash}{timestamp}{container_id}{temp:.2f}{rsl:.2f}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def get_last_hash(container_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT block_hash FROM telemetry WHERE container_id = ? ORDER BY id DESC LIMIT 1", (container_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"

def calculate_arrhenius_decay(temp_celsius, base_temp, ea_factor):
    temp_diff = max(0.0, temp_celsius - base_temp)
    return float(np.exp(ea_factor * temp_diff))

def evaluate_status(remaining_rsl, initial_rsl, current_cargo_temp, max_safe_temp, critical_temp, roc, roc_limit):
    if remaining_rsl <= 0 or current_cargo_temp >= critical_temp:
        return "COMPROMISED"
    elif remaining_rsl < (initial_rsl * 0.4) or current_cargo_temp > max_safe_temp or roc > roc_limit:
        return "AT-RISK"
    else:
        return "NOMINAL"

def log_telemetry_entry(container_id, cargo_type, ambient_temp, cargo_temp, humidity, roc, decay_rate, rsl, lat, lon, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prev_hash = get_last_hash(container_id)
    block_hash = generate_block_hash(prev_hash, timestamp, container_id, cargo_temp, rsl)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO telemetry (
            timestamp, container_id, cargo_type, ambient_temp, 
            cargo_temp, humidity, rate_of_change, decay_rate, 
            remaining_shelf_life_hrs, lat, lon, status, prev_hash, block_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, container_id, cargo_type, ambient_temp, cargo_temp, humidity, roc, decay_rate, rsl, lat, lon, status, prev_hash, block_hash))
    conn.commit()
    conn.close()

def get_telemetry_history(container_id=None):
    conn = sqlite3.connect(DB_NAME)
    if container_id:
        df = pd.read_sql_query("SELECT * FROM telemetry WHERE container_id = ? ORDER BY id DESC LIMIT 50", conn, params=(container_id,))
    else:
        df = pd.read_sql_query("SELECT * FROM telemetry ORDER BY id DESC LIMIT 100", conn)
    conn.close()
    return df

def clear_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM telemetry")
    conn.commit()
    conn.close()

def predict_time_to_breach(df_hist, critical_temp):
    """Uses Linear Regression on recent telemetry to predict time until critical failure."""
    if len(df_hist) < 5:
        return None
    
    # Take the last 10 points for a short-term trend
    recent_data = df_hist.head(10).iloc[::-1].reset_index()
    X = np.array(recent_data.index).reshape(-1, 1) # Time steps
    y = np.array(recent_data['cargo_temp'])
    
    model = LinearRegression()
    model.fit(X, y)
    
    trend = model.coef_[0]
    if trend <= 0.05:  # Temperature is stable or cooling
        return "> 60"
    
    current_temp = y[-1]
    steps_to_critical = (critical_temp - current_temp) / trend
    minutes = steps_to_critical * (5/60) # Assuming 5 sec intervals
    
    return max(0, minutes)
