from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)

# Default starting coordinates near VIT Vellore campus
latest_data = {
    "shipment_id": "UNIT-ALPHA-101",
    "cargo_temp": 0,
    "ambient_temp": 0,
    "humidity": 0,
    "compressor_failure": False,
    "lat": 12.9692, 
    "lon": 79.1559
}

last_updated = None

@app.route("/telemetry", methods=["POST"])
def receive_telemetry():
    global latest_data, last_updated
    raw_data = request.get_data(as_text=True)

    try:
        incoming_data = json.loads(raw_data)
        latest_data.update(incoming_data) # Update only provided fields
        last_updated = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Payload Received: {latest_data['cargo_temp']}°C | GPS: {latest_data['lat']}, {latest_data['lon']}")
        return jsonify({"status": "received"}), 200
    except Exception as e:
        print("JSON ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/telemetry", methods=["GET"])
def get_telemetry():
    data = latest_data.copy()
    data["last_updated"] = last_updated
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
