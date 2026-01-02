# backend/routes/worker.py

from flask import Blueprint, render_template, current_app
from services.firebase import get_firestore, get_live_ref
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
    
    # Get comprehensive, today-focused statistics from Firestore
    stats = get_daily_worker_stats(device_id)
    
    # Get a list of today's drowsiness events
    today_events = get_today_drowsiness_events(device_id)
    
    # Get data for the currently active session from Firestore
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
    Calculate daily statistics by scanning Firestore documents.
    This avoids reliance on complex, pre-built indexes.
    """
    try:
        db = get_firestore()
        today_utc = datetime.now(timezone.utc).date()
        
        total_seconds_today = 0
        session_count_today = 0
        drowsy_events_today = 0

        # Scan sessions that started today
        sessions_ref = db.collection("sessions").where('device_id', '==', device_id)
        for session_doc in sessions_ref.stream():
            session = session_doc.to_dict()
            start_time = session.get("start_time")
            if start_time and isinstance(start_time, datetime) and start_time.date() == today_utc:
                session_count_today += 1
                end_time = session.get("end_time") or datetime.now(timezone.utc)
                if end_time.tzinfo is None: end_time = end_time.replace(tzinfo=timezone.utc)
                if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=timezone.utc)
                total_seconds_today += (end_time - start_time).total_seconds()

        # Scan drowsy events that happened today
        events_ref = db.collection("drowsy_events").where('device_id', '==', device_id)
        for event_doc in events_ref.stream():
            event = event_doc.to_dict()
            timestamp = event.get("timestamp")
            if timestamp and isinstance(timestamp, datetime) and timestamp.date() == today_utc:
                drowsy_events_today += 1
        
        daily_hours = round(total_seconds_today / 3600, 1)
        avg_duration = round(daily_hours / session_count_today, 1) if session_count_today > 0 else 0.0
        
        return {
            "daily_worked_hours": daily_hours,
            "today_drowsy_events": drowsy_events_today,
            "today_total_sessions": session_count_today,
            "today_avg_session_duration": avg_duration,
        }
    except Exception as e:
        print(f"ERROR getting daily worker stats: {e}")
        return {"daily_worked_hours": 0, "today_drowsy_events": 0, "today_total_sessions": 0, "today_avg_session_duration": 0}

def get_today_drowsiness_events(device_id, limit=50):
    """
    Get today's drowsiness events, newest first, directly from Firestore.
    """
    try:
        db = get_firestore()
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        query = db.collection("drowsy_events") \
                  .where("device_id", "==", device_id) \
                  .where("timestamp", ">=", today_start) \
                  .order_by("timestamp", direction="DESCENDING") \
                  .limit(limit)
                  
        return [doc.to_dict() for doc in query.stream()]
    except Exception as e:
        print(f"ERROR getting today's events: {e}")
        return []

def get_current_session_data(device_id):
    """
    Gets the current active session (end_time is None) directly from Firestore.
    This is robust across processes.
    """
    try:
        db = get_firestore()
        query = db.collection("sessions") \
                  .where("device_id", "==", device_id) \
                  .where("end_time", "==", None) \
                  .limit(1)

        results = list(query.stream())
        if not results:
            return None

        session_doc = results[0]
        session = session_doc.to_dict()
        session["id"] = session_doc.id
        start_time = session.get("start_time")

        if start_time and isinstance(start_time, datetime):
            if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=timezone.utc)
            duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            session["duration_hours"] = max(0, duration_seconds) / 3600
        
        return session
    except Exception as e:
        print(f"ERROR getting current session data: {e}")
        return None




