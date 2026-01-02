# backend/services/work_hours.py

from datetime import datetime, timezone
from services.firebase import get_firestore

# ===============================
# Session Duration
# ===============================
def calculate_session_duration(session):
    """
    Calculate duration of a single session in seconds.
    Handles both completed and ongoing sessions, ensuring timezone awareness.
    """
    start = session.get("start_time")
    end = session.get("end_time") or datetime.now(timezone.utc)

    if not start or not isinstance(start, datetime):
        return 0
    
    if not isinstance(end, datetime):
        end = datetime.now(timezone.utc)

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    duration = (end - start).total_seconds()
    return max(duration, 0)

# ===============================
# Total Worked Hours
# ===============================
def get_total_worked_hours(device_id):
    """
    Calculate total worked hours by scanning all sessions.
    """
    try:
        db = get_firestore()
        sessions_stream = db.collection("sessions").stream()
        total_seconds = 0

        for s in sessions_stream:
            session = s.to_dict()
            if session.get("device_id") == device_id:
                total_seconds += calculate_session_duration(session)

        return round(total_seconds / 3600, 2)
    except Exception as e:
        print(f"ERROR calculating total worked hours: {e}")
        return 0.0

# ===============================
# Daily Worked Hours
# ===============================
def get_daily_worked_hours(device_id, date_str):
    """
    Calculate worked hours for a specific day by scanning all sessions.
    """
    try:
        db = get_firestore()
        sessions_stream = db.collection("sessions").stream()
        total_seconds = 0
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        for s in sessions_stream:
            session = s.to_dict()
            if session.get("device_id") != device_id:
                continue

            start_time = session.get("start_time")
            if not start_time or not isinstance(start_time, datetime):
                continue

            if start_time.date() == target_date:
                total_seconds += calculate_session_duration(session)

        return round(total_seconds / 3600, 2)
    except Exception as e:
        print(f"ERROR calculating daily worked hours: {e}")
        return 0.0

# ===============================
# Inactivity Detection (Restored)
# ===============================
def is_inactive(last_timestamp, threshold_minutes=10):
    """
    Detect if the helmet is inactive based on the last update time.
    """
    if not last_timestamp or not isinstance(last_timestamp, datetime):
        return True

    # Ensure timestamp is timezone-aware for correct comparison
    if last_timestamp.tzinfo is None:
        last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)

    delta_seconds = (datetime.now(timezone.utc) - last_timestamp).total_seconds()
    return delta_seconds > threshold_minutes * 60
