from flask import Blueprint, render_template, current_app
from datetime import datetime

from services.firebase import get_live_ref, safe_get, get_firestore
from services.work_hours import (
    get_total_worked_hours,
    get_daily_worked_hours
)
from services.alerts import get_recent_alerts
from services.session_tracker import get_active_session_id

worker_bp = Blueprint("worker", __name__)

@worker_bp.route("/worker/<device_id>")
def worker_dashboard(device_id):
    db = get_firestore()

    # ================= LIVE =================
    live = safe_get(get_live_ref(device_id), {})

    # ================= SESSIONS =================
    active_session_id = get_active_session_id(device_id)
    session_data = None

    if active_session_id:
        doc = db.collection("sessions").document(active_session_id).get()
        if doc.exists:
            s = doc.to_dict()
            start = s.get("start_time")
            duration = 0
            if start:
                duration = round((datetime.utcnow() - start).total_seconds() / 3600, 2)

            session_data = {
                "start_time": start,
                "duration_hours": duration,
                "total_drowsy_events": s.get("total_drowsy_events", 0)
            }

    # ================= STATS =================
    today = datetime.utcnow().strftime("%Y-%m-%d")

    stats = {
        "total_worked_hours": get_total_worked_hours(device_id),
        "daily_worked_hours": get_daily_worked_hours(device_id, today),
        "total_drowsy_events": db.collection("drowsy_events")
                                   .where("device_id", "==", device_id)
                                   .stream().__length_hint__(),
        "today_drowsy_events": 0,
        "total_sessions": db.collection("sessions")
                             .where("device_id", "==", device_id)
                             .stream().__length_hint__(),
        "active_sessions": 1 if session_data else 0,
        "avg_session_duration": 0,
        "week_drowsy_events": 0
    }

    # ================= EVENTS =================
    today_events = []
    events = db.collection("drowsy_events") \
        .where("device_id", "==", device_id) \
        .order_by("timestamp", direction="DESCENDING") \
        .limit(20).stream()

    for e in events:
        ev = e.to_dict()
        if ev.get("timestamp") and ev["timestamp"].strftime("%Y-%m-%d") == today:
            today_events.append(ev)

    # ================= ALERTS =================
    alerts = get_recent_alerts(device_id)

    # ================= PATTERNS =================
    behavior_patterns = {
        "most_common_time": None,
        "avg_temperature_during_drowsy": None,
        "avg_heart_rate_during_drowsy": None
    }

    return render_template(
        "worker_dashboard.html",
        device_id=device_id,
        live=live,
        stats=stats,
        session_data=session_data,
        behavior_patterns=behavior_patterns,
        today_events=today_events,
        alerts=alerts
    )
