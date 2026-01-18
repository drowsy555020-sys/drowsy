# backend/services/analytics.py

from datetime import datetime, timezone
from services.firebase import get_firestore


def log_drowsiness_event(device_id, live_data):
    """
    Logs a specific drowsiness event with its context.

    Note:
        Old Firestore-based session creation/end logic has been removed.
        Sessions are now tracked exclusively in Firebase Realtime Database
        under /devices/{device_id}/history.
    """
    try:
        db = get_firestore()
        event_ref = db.collection("drowsy_events").document()
        event_data = {
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc),
            "pitch": live_data.get("pitch"),
            "temperature": live_data.get("bodyTemp"),
        }
        event_ref.set(event_data)
    except Exception as e:
        print(f"ERROR logging drowsiness event: {e}")
