# backend/routes/api.py

from flask import Blueprint, request, jsonify, current_app
from services.firebase import (
    get_live_ref,
    get_control_ref
)
from services.analytics import log_drowsiness_event
from services.alerts import generate_alerts
from services.work_hours import is_inactive
from datetime import datetime

api_bp = Blueprint("api", __name__)

# ===============================
# POST: ESP32 → Live Data
# ===============================
@api_bp.route("/telemetry", methods=["POST"])
def receive_telemetry():
    """
    ESP32 pushes live sensor data here
    """
    data = request.json
    device_id = current_app.config["DEVICE_ID"]

    if not data:
        return jsonify({"error": "No data"}), 400

    # Add server timestamp
    data["serverTime"] = int(datetime.utcnow().timestamp())

    # Push to Firebase Realtime DB
    live_ref = get_live_ref(device_id)
    live_ref.update(data)

    # -------- Analytics --------
    if data.get("isDrowsy"):
        log_drowsiness_event(device_id, data)

    # -------- Alerts --------
    alerts = generate_alerts(device_id, data)

    return jsonify({
        "status": "OK",
        "alerts_generated": len(alerts)
    })


# ===============================
# GET: Live Data (Dashboard)
# ===============================
@api_bp.route("/live", methods=["GET"])
def get_live_data():
    """
    Dashboard fetches live telemetry
    """
    device_id = current_app.config["DEVICE_ID"]
    live_ref = get_live_ref(device_id)

    data = live_ref.get()
    return jsonify({
        "device_id": device_id,
        "live": data
    })


# ===============================
# GET: Motor State
# ===============================
@api_bp.route("/motor", methods=["GET"])
def get_motor_state():
    device_id = current_app.config["DEVICE_ID"]
    control_ref = get_control_ref(device_id)

    state = control_ref.get()
    return jsonify({
        "motor": state.get("motor", "UNKNOWN")
    })


# ===============================
# GET: Inactivity Check
# ===============================
@api_bp.route("/inactive", methods=["GET"])
def check_inactivity():
    """
    Detect device inactivity
    """
    device_id = current_app.config["DEVICE_ID"]
    live = get_live_ref(device_id).get()

    last_ts = None
    if live and "serverTime" in live:
        last_ts = datetime.utcfromtimestamp(live["serverTime"])

    inactive = is_inactive(last_ts)

    return jsonify({
        "device_id": device_id,
        "inactive": inactive
    })
