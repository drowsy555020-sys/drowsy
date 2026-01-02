# backend/services/session_tracker.py

from datetime import datetime, timezone, timedelta
from services.firebase import get_firestore, get_live_ref
from services.analytics import start_session, end_session, increment_drowsy_count, log_drowsiness_event

# If we haven't received a heartbeat in 60 seconds, consider the device offline.
OFFLINE_THRESHOLD = timedelta(seconds=60)

def _find_active_session(db, device_id):
    """Helper to find an active session (end_time is None) in Firestore."""
    try:
        query = db.collection("sessions").where("device_id", "==", device_id).where("end_time", "==", None).limit(1)
        results = list(query.stream())
        if results:
            doc = results[0]
            return doc.id, doc.to_dict()
    except Exception as e:
        print(f"ERROR finding active session: {e}")
    return None, None

def check_and_update_sessions(device_id):
    """
    Manages worker sessions using a reliable timestamp-based method.
    This version CORRECTLY handles the millisecond timestamp from Firebase RTDB and ensures its type.
    """
    try:
        live_data = get_live_ref(device_id).get()
        db = get_firestore()
        active_session_id, _ = _find_active_session(db, device_id)

        is_online = False
        if live_data and "serverTime" in live_data:
            try:
                # FINAL CRITICAL FIX: Ensure serverTime is a number before calculation.
                server_timestamp_ms = float(live_data["serverTime"])
                last_heartbeat = datetime.fromtimestamp(server_timestamp_ms / 1000, tz=timezone.utc)
                
                time_since_heartbeat = datetime.now(timezone.utc) - last_heartbeat
                if time_since_heartbeat <= OFFLINE_THRESHOLD:
                    is_online = True
            except (ValueError, TypeError) as e:
                # If serverTime is not a valid number, treat as offline and log error.
                print(f"WARNING: Could not parse serverTime '{live_data.get('serverTime')}'. Error: {e}")
                is_online = False

        if is_online:
            # --- DEVICE IS ONLINE ---
            if not active_session_id:
                new_session_id = start_session(device_id)
                print(f"[Session] Device is ONLINE. Started new session: {new_session_id}")
                return
            else:
                if live_data.get("isDrowsy"):
                    increment_drowsy_count(active_session_id)
                    log_drowsiness_event(device_id, live_data)
        
        else:
            # --- DEVICE IS OFFLINE ---
            if active_session_id:
                print(f"[Session] Device is OFFLINE (stale or invalid timestamp). Ending session: {active_session_id}")
                end_session(active_session_id)
            
    except Exception as e:
        print(f"ERROR in session tracker for {device_id}: {e}")
