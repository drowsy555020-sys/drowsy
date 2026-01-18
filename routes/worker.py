from flask import Blueprint, render_template, current_app
from services.firebase import get_firestore, get_live_ref
from services.work_hours import get_daily_worked_hours, get_rtdb_sessions
from datetime import datetime, timezone

worker_bp = Blueprint("worker", __name__)


@worker_bp.route("/worker-dashboard")
def worker_dashboard():
    """
    Worker behavior dashboard with redesigned, clearer statistics.
    """
    device_id = current_app.config["DEVICE_ID"]

    # Get live sensor data for immediate status
    live_data = get_live_ref(device_id).get() or {}

    # Get comprehensive, today-focused statistics based on RTDB sessions
    stats = get_daily_worker_stats(device_id)

    # Get a list of today's drowsiness events
    today_events = get_today_drowsiness_events(device_id)

    # Get data for the currently active session from RTDB
    session_data = get_current_session_data(device_id)

    return render_template(
        "worker_dashboard.html",
        device_id=device_id,
        live=live_data,
        stats=stats,
        today_events=today_events,
        session_data=session_data,
    )


def get_daily_worker_stats(device_id):
    """
    Calculate daily statistics using RTDB sessions + Firestore drowsy events.
    """
    try:
        db = get_firestore()
        today_utc = datetime.now(timezone.utc).date()

        # ---- Sessions from RTDB ----
        date_str = today_utc.strftime("%Y-%m-%d")
        daily_hours = get_daily_worked_hours(device_id, date_str)
        sessions = get_rtdb_sessions(device_id)
        session_count_today = 0

        for s in sessions:
            start_time = s.get("start_time")
            if start_time and isinstance(start_time, datetime) and start_time.date() == today_utc:
                session_count_today += 1

        avg_duration = (
            round(daily_hours / session_count_today, 1) if session_count_today > 0 else 0.0
        )

        # ---- Drowsy events from Firestore ----
        drowsy_events_today = 0
        events_ref = db.collection("drowsy_events").where("device_id", "==", device_id)
        for event_doc in events_ref.stream():
            event = event_doc.to_dict()
            timestamp = event.get("timestamp")
            if timestamp and isinstance(timestamp, datetime) and timestamp.date() == today_utc:
                drowsy_events_today += 1

        return {
            "daily_worked_hours": round(daily_hours, 1),
            "today_drowsy_events": drowsy_events_today,
            "today_total_sessions": session_count_today,
            "today_avg_session_duration": avg_duration,
        }
    except Exception as e:
        print(f"ERROR getting daily worker stats (RTDB): {e}")
        return {
            "daily_worked_hours": 0,
            "today_drowsy_events": 0,
            "today_total_sessions": 0,
            "today_avg_session_duration": 0,
        }


def get_today_drowsiness_events(device_id, limit=50):
    """
    Get today's drowsiness events, newest first, directly from Firestore.
    """
    try:
        db = get_firestore()
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        query = (
            db.collection("drowsy_events")
            .where("device_id", "==", device_id)
            .where("timestamp", ">=", today_start)
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
        )

        return [doc.to_dict() for doc in query.stream()]
    except Exception as e:
        print(f"ERROR getting today's events: {e}")
        return []


def get_current_session_data(device_id):
    """
    Get the current active session from RTDB history.
    A session is considered active if its 'active' flag is True.
    """
    try:
        sessions = get_rtdb_sessions(device_id)
        active_sessions = [s for s in sessions if s.get("active")]
        if not active_sessions:
            return None

        # Pick the most recent active session
        latest = max(
            active_sessions,
            key=lambda s: s.get("start_time") or datetime.min.replace(tzinfo=timezone.utc),
        )

        duration_hours = round(latest.get("duration_seconds", 0.0) / 3600.0, 2)

        return {
            "id": latest.get("id"),
            "start_time": latest.get("start_time"),
            "duration_hours": duration_hours,
            # We no longer track per-session drowsy counts; default to 0 for UI compatibility
            "total_drowsy_events": 0,
        }
    except Exception as e:
        print(f"ERROR getting current session data from RTDB: {e}")
        return None
