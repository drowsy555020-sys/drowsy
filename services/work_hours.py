# backend/services/work_hours.py

from datetime import datetime, timezone
from services.firebase import get_device_ref, safe_get


# ===============================
# RTDB Session Helpers
# ===============================
def _parse_rtdb_timestamp(value):
    """
    Convert an RTDB millisecond (or second) timestamp to a timezone-aware datetime.
    """
    if value is None:
        return None
    try:
        ts = float(value)
        # Heuristic: large values are usually in milliseconds
        if ts > 1e11:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None


def _load_rtdb_history(device_id):
    """
    Load the session history from RTDB:
        /devices/{device_id}/history
    """
    history_ref = get_device_ref(device_id).child("history")
    history = safe_get(history_ref, {}) or {}
    # Ensure we always return a dict
    if isinstance(history, dict):
        return history
    return {}


def get_rtdb_sessions(device_id):
    """
    Return a normalized list of sessions from RTDB history.

    Each session dict contains:
        - id: RTDB key
        - start_time: datetime or None
        - end_time: datetime or None
        - active: bool
        - duration_seconds: float
    """
    history = _load_rtdb_history(device_id)
    sessions = []
    now = datetime.now(timezone.utc)

    for sid, raw in history.items():
        if not isinstance(raw, dict):
            continue

        start_dt = _parse_rtdb_timestamp(raw.get("startTime"))
        end_dt = _parse_rtdb_timestamp(raw.get("endTime")) if raw.get("endTime") else None
        active = bool(raw.get("active", False))

        duration_seconds = 0.0
        try:
            if "finalDuration" in raw:
                duration_seconds = float(raw["finalDuration"])
            elif "duration" in raw:
                duration_seconds = float(raw["duration"])
            elif start_dt:
                end_for_duration = end_dt or now
                duration_seconds = max((end_for_duration - start_dt).total_seconds(), 0.0)
        except Exception:
            duration_seconds = 0.0

        sessions.append(
            {
                "id": sid,
                "start_time": start_dt,
                "end_time": end_dt,
                "active": active,
                "duration_seconds": duration_seconds,
                # Kept for template compatibility; RTDB does not track this per-session.
                "total_drowsy_events": 0,
            }
        )

    return sessions


# ===============================
# Total Worked Hours (RTDB)
# ===============================
def get_total_worked_hours(device_id):
    """
    Calculate total worked hours using RTDB session history.
    """
    try:
        sessions = get_rtdb_sessions(device_id)
        total_seconds = sum(s.get("duration_seconds", 0.0) for s in sessions)
        return round(total_seconds / 3600.0, 2)
    except Exception as e:
        print(f"ERROR calculating total worked hours from RTDB: {e}")
        return 0.0


# ===============================
# Daily Worked Hours (RTDB)
# ===============================
def get_daily_worked_hours(device_id, date_str):
    """
    Calculate worked hours for a specific day using RTDB session history.
    A session is counted for the day based on its start_time date.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        sessions = get_rtdb_sessions(device_id)
        total_seconds = 0.0

        for s in sessions:
            start_time = s.get("start_time")
            if not start_time or not isinstance(start_time, datetime):
                continue
            if start_time.date() != target_date:
                continue
            total_seconds += s.get("duration_seconds", 0.0)

        return round(total_seconds / 3600.0, 2)
    except Exception as e:
        print(f"ERROR calculating daily worked hours from RTDB: {e}")
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
