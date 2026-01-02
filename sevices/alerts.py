# backend/services/alerts.py

from datetime import datetime
from services.firebase import get_firestore
from google.api_core import exceptions as google_exceptions

# ===============================
# Alert Rules (Easy to Tune)
# ===============================
TEMP_THRESHOLD = 38.5
PITCH_THRESHOLD = -20
GYRO_Y_THRESHOLD = -120


# ===============================
# Alert Generator
# ===============================
def generate_alerts(device_id, live_data):
    """
    Evaluate live sensor data and generate alerts
    """
    alerts = []

    pitch = live_data.get("pitch", 0)
    gyroY = live_data.get("gyroY", 0)
    temp = live_data.get("bodyTemp", 0)
    is_drowsy = live_data.get("isDrowsy", False)

    timestamp = datetime.utcnow()

    # ---- Drowsiness Alert ----
    if is_drowsy:
        alerts.append(create_alert(
            device_id,
            "DROWSINESS_DETECTED",
            "Driver drowsiness detected. Motor stopped.",
            timestamp
        ))

    # ---- Head Down Alert ----
    if pitch < PITCH_THRESHOLD:
        alerts.append(create_alert(
            device_id,
            "HEAD_DOWN",
            f"Abnormal head tilt detected (pitch={pitch:.1f})",
            timestamp
        ))

    # ---- Sudden Nod Alert ----
    if gyroY < GYRO_Y_THRESHOLD:
        alerts.append(create_alert(
            device_id,
            "SUDDEN_NOD",
            f"Sudden head nod detected (gyroY={gyroY:.1f})",
            timestamp
        ))

    # ---- High Temperature Alert ----
    if temp > TEMP_THRESHOLD:
        alerts.append(create_alert(
            device_id,
            "HIGH_BODY_TEMPERATURE",
            f"High body temperature detected ({temp:.1f} °C)",
            timestamp
        ))

    # Save all alerts
    for alert in alerts:
        save_alert(alert)

    return alerts


# ===============================
# Alert Object
# ===============================
def create_alert(device_id, alert_type, message, timestamp):
    return {
        "device_id": device_id,
        "type": alert_type,
        "message": message,
        "timestamp": timestamp,
        "acknowledged": False
    }


# ===============================
# Firestore Logging
# ===============================
def save_alert(alert):
    """
    Store alert in Firestore
    """
    db = get_firestore()
    db.collection("alerts").add(alert)


# ===============================
# Fetch Alerts
# ===============================
def get_recent_alerts(device_id, limit=10):
    """
    Fetch recent alerts for dashboard
    Handles missing Firestore indexes gracefully
    """
    try:
        db = get_firestore()
        from google.cloud.firestore_v1.base_query import FieldFilter
        docs = db.collection("alerts") \
                 .where(filter=FieldFilter("device_id", "==", device_id)) \
                 .order_by("timestamp", direction="DESCENDING") \
                 .limit(limit) \
                 .stream()

        return [doc.to_dict() for doc in docs]
    except google_exceptions.FailedPrecondition as e:
        # Index not created yet - return empty list
        print(f"Warning: Firestore index not found. Please create the index: {e}")
        return []
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return []


# ===============================
# Acknowledge Alert
# ===============================
def acknowledge_alert(alert_id):
    """
    Mark alert as acknowledged
    """
    db = get_firestore()
    db.collection("alerts").document(alert_id).update({
        "acknowledged": True
    })
