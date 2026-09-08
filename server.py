from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)

latest_data = {
    "shipment_id": "UNIT-ALPHA-101",
    "cargo_temp": 0,
    "ambient_temp": 0,
    "humidity": 0,
    "compressor_failure": False
}

# Time when valid ESP32 telemetry was last received
last_updated = None


@app.route("/telemetry", methods=["POST"])
def receive_telemetry():
    global latest_data, last_updated

    raw_data = request.get_data(as_text=True)

    print("\nRAW DATA FROM ESP32:")
    print(raw_data)

    try:
        latest_data = json.loads(raw_data)

        # Update only after valid telemetry is received
        last_updated = time.time()

        print("\nParsed data:")
        print(latest_data)

        return jsonify({
            "status": "received"
        }), 200

    except Exception as e:
        print("JSON ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route("/telemetry", methods=["GET"])
def get_telemetry():

    data = latest_data.copy()

    data["last_updated"] = last_updated

    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
