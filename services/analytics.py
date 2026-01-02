# backend/services/analytics.py

from datetime import datetime, timezone
from services.firebase import get_firestore

def start_session(device_id):
    """Starts a new session and returns its unique ID."""
    try:
        db = get_firestore()
        session_ref = db.collection("sessions").document()
        session_data = {
            "device_id": device_id,
            "start_time": datetime.now(timezone.utc),
            "end_time": None, # Mark as active
            "total_drowsy_events": 0
        }
        session_ref.set(session_data)
        return session_ref.id
    except Exception as e:
        print(f"ERROR starting session: {e}")
        return None

def end_session(session_id):
    """
    Correctly ends an active session by updating its end_time.
    This fixes the critical bug where disconnecting created a new session.
    """
    try:
        db = get_firestore()
        session_ref = db.collection("sessions").document(session_id)
        # Atomically update the end_time field of the specific session document.
        session_ref.update({"end_time": datetime.now(timezone.utc)})
    except Exception as e:
        print(f"ERROR ending session {session_id}: {e}")

def increment_drowsy_count(session_id):
    """Increments the drowsiness counter for a given session."""
    try:
        db = get_firestore()
        session_ref = db.collection("sessions").document(session_id)
        # Using Firestore's atomic increment operation.
        session_ref.update({"total_drowsy_events": get_firestore.Increment(1)})
    except Exception as e:
        print(f"ERROR incrementing drowsy count for session {session_id}: {e}")

def log_drowsiness_event(device_id, live_data):
    """Logs a specific drowsiness event with its context."""
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
