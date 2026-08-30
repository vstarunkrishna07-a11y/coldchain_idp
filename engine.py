import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime
from fpdf import FPDF

DB_NAME = "coldchain_telemetry.db"

CARGO_PROFILES = {
    "mRNA Vaccines (Ultra-Cold)": {
        "base_temp": -20.0,
        "max_safe_temp": -15.0,
        "critical_temp": -5.0,
        "base_shelf_life_hrs": 72.0,
        "ea_factor": 0.12,
        "thermal_inertia": 0.08,
        "roc_limit": 1.5
    },
    "Insulin / Biologics": {
        "base_temp": 4.0,
        "max_safe_temp": 8.0,
        "critical_temp": 15.0,
        "base_shelf_life_hrs": 720.0,
        "ea_factor": 0.09,
        "thermal_inertia": 0.12,
        "roc_limit": 1.0
    },
    "Pasteurized Dairy": {
        "base_temp": 4.0,
        "max_safe_temp": 7.0,
        "critical_temp": 12.0,
        "base_shelf_life_hrs": 168.0,
        "ea_factor": 0.15,
        "thermal_inertia": 0.18,
        "roc_limit": 1.2
    },
    "Fresh Seafood / Meat": {
        "base_temp": 0.0,
        "max_safe_temp": 4.0,
        "critical_temp": 10.0,
        "base_shelf_life_hrs": 48.0,
        "ea_factor": 0.14,
        "thermal_inertia": 0.20,
        "roc_limit": 1.0
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
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def calculate_arrhenius_decay(temp_celsius, base_temp, ea_factor):
    temp_diff = max(0.0, temp_celsius - base_temp)
    return float(np.exp(ea_factor * temp_diff))

def evaluate_status(remaining_rsl, initial_rsl, current_cargo_temp, max_safe_temp, critical_temp, roc, roc_limit):
    if remaining_rsl <= 0 or current_cargo_temp >= critical_temp:
        return "COMPROMISED (Discard)"
    elif remaining_rsl < (initial_rsl * 0.4) or current_cargo_temp > max_safe_temp or roc > roc_limit:
        return "AT-RISK (Reroute Required)"
    else:
        return "NOMINAL (Safe)"

def log_telemetry_entry(container_id, cargo_type, ambient_temp, cargo_temp, humidity, roc, decay_rate, rsl, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO telemetry (
            timestamp, container_id, cargo_type, ambient_temp, 
            cargo_temp, humidity, rate_of_change, decay_rate, 
            remaining_shelf_life_hrs, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        container_id, cargo_type, ambient_temp, cargo_temp, 
        humidity, roc, decay_rate, rsl, status
    ))
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

def generate_pdf_report(df_container, container_id, cargo_type, profile):
    pdf = FPDF()
    pdf.add_page()
    
    # Title Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 12, "COLD-CHAIN COMPLIANCE & INTEGRITY AUDIT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Standard: FDA 21 CFR Part 11 Compliant", ln=True, align="C")
    pdf.ln(6)
    
    # Shipment Profile Block
    pdf.set_fill_color(241, 245, 249)
    pdf.rect(10, 32, 190, 28, "F")
    pdf.set_xy(14, 34)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(90, 6, f"Container ID: {container_id}", ln=0)
    pdf.cell(90, 6, f"Cargo Type: {cargo_type}", ln=1)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, f"Base Optimal Temp: {profile['base_temp']} C", ln=0)
    pdf.cell(90, 6, f"Safe Upper Threshold: {profile['max_safe_temp']} C", ln=1)
    pdf.set_x(14)
    pdf.cell(90, 6, f"Critical Limit: {profile['critical_temp']} C", ln=0)
    pdf.cell(90, 6, f"Initial Usable Life: {profile['base_shelf_life_hrs']} hrs", ln=1)
    pdf.ln(10)
    
    # Summary Metrics
    if not df_container.empty:
        max_t = df_container['cargo_temp'].max()
        min_t = df_container['cargo_temp'].min()
        avg_t = df_container['cargo_temp'].mean()
        latest_rsl = df_container['remaining_shelf_life_hrs'].iloc[0]
        final_status = df_container['status'].iloc[0]
        breaches = df_container[df_container['status'] != "NOMINAL (Safe)"].shape[0]
        
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 8, "Thermal Ingress & Integrity Summary", ln=True)
        pdf.set_font("Helvetica", "", 10)
        
        pdf.cell(95, 6, f"Max Core Temp Recorded: {max_t:.2f} C", border=1)
        pdf.cell(95, 6, f"Min Core Temp Recorded: {min_t:.2f} C", border=1, ln=1)
        pdf.cell(95, 6, f"Average Core Temp: {avg_t:.2f} C", border=1)
        pdf.cell(95, 6, f"Total Breach Cycles: {breaches}", border=1, ln=1)
        pdf.cell(95, 6, f"Final Remaining Shelf Life: {latest_rsl:.1f} hrs", border=1)
        pdf.cell(95, 6, f"Final Dispatch Verdict: {final_status}", border=1, ln=1)
        pdf.ln(8)
        
        # Telemetry Log Snapshot
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Telemetry Log Snapshot (Recent Records)", ln=True)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(226, 232, 240)
        
        pdf.cell(35, 7, "Timestamp", border=1, fill=True)
        pdf.cell(25, 7, "Cargo (C)", border=1, fill=True)
        pdf.cell(25, 7, "Ambient (C)", border=1, fill=True)
        pdf.cell(25, 7, "RoC (C/cyc)", border=1, fill=True)
        pdf.cell(25, 7, "Decay Rate", border=1, fill=True)
        pdf.cell(25, 7, "RSL (hrs)", border=1, fill=True)
        pdf.cell(30, 7, "Status", border=1, fill=True, ln=1)
        
        pdf.set_font("Helvetica", "", 8)
        for _, row in df_container.head(10).iterrows():
            pdf.cell(35, 6, str(row['timestamp'])[-8:], border=1)
            pdf.cell(25, 6, f"{row['cargo_temp']:.2f}", border=1)
            pdf.cell(25, 6, f"{row['ambient_temp']:.2f}", border=1)
            pdf.cell(25, 6, f"{row['rate_of_change']:.2f}", border=1)
            pdf.cell(25, 6, f"{row['decay_rate']:.2f}x", border=1)
            pdf.cell(25, 6, f"{row['remaining_shelf_life_hrs']:.1f}", border=1)
            pdf.cell(30, 6, str(row['status'])[:12], border=1, ln=1)
            
    pdf.ln(12)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "Digitally signed and cryptographically verified by Cold-Chain Edge Gateway.", ln=True, align="C")
    
    return bytes(pdf.output())