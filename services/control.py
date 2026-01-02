# backend/routes/control.py

from flask import Blueprint, request, jsonify, current_app
from services.firebase import get_control_ref
from datetime import datetime

control_bp = Blueprint("control", __name__)

VALID_STATES = ["ON", "OFF"]


# ===============================
# POST: Motor Control
# ===============================
@control_bp.route("/motor", methods=["POST"])
def set_motor_state():
    """
    Dashboard / Admin controls motor
    """
    device_id = current_app.config["DEVICE_ID"]
    data = request.json

    if not data or "state" not in data:
        return jsonify({"error": "Missing motor state"}), 400

    state = data["state"].upper()

    if state not in VALID_STATES:
        return jsonify({
            "error": "Invalid state",
            "allowed": VALID_STATES
        }), 400

    control_ref = get_control_ref(device_id)

    control_ref.update({
        "motor": state,
        "updated_at": int(datetime.utcnow().timestamp()),
        "source": "dashboard"
    })

    return jsonify({
        "status": "OK",
        "device_id": device_id,
        "motor": state
    })


# ===============================
# POST: Emergency Stop
# ===============================
@control_bp.route("/emergency-stop", methods=["POST"])
def emergency_stop():
    """
    Immediate motor shutdown (highest priority)
    """
    device_id = current_app.config["DEVICE_ID"]
    control_ref = get_control_ref(device_id)

    control_ref.update({
        "motor": "OFF",
        "updated_at": int(datetime.utcnow().timestamp()),
        "source": "emergency"
    })

    return jsonify({
        "status": "EMERGENCY_STOP_ACTIVATED",
        "device_id": device_id
    })
