# backend/routes/dashboard.py

from flask import Blueprint, render_template, current_app
from services.firebase import get_live_ref, get_firestore, safe_get
from services.alerts import get_recent_alerts
from services.work_hours import get_total_worked_hours, get_rtdb_sessions
from google.api_core import exceptions as google_exceptions

from datetime import datetime, timezone

dashboard_bp = Blueprint("dashboard", __name__)


# ===============================
# Dashboard Home
# ===============================
@dashboard_bp.route("/")
def dashboard():
    device_id = current_app.config["DEVICE_ID"]

    # ---- Live Data ----
    live_data = safe_get(get_live_ref(device_id), {})

    # ---- Alerts ----
    alerts = get_recent_alerts(device_id)

    # ---- Worked Hours ----
    worked_hours = get_total_worked_hours(device_id)

    return render_template(
        "dashboard.html",
        device_id=device_id,
        live=live_data,
        alerts=alerts,
        worked_hours=worked_hours,
    )


# ===============================
# Drowsiness History Page
# ===============================
@dashboard_bp.route("/drowsiness-history")
def drowsiness_history():
    device_id = current_app.config["DEVICE_ID"]
    from datetime import datetime, date

    try:
        db = get_firestore()
        events = []

        # Try with index first
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter

            docs = (
                db.collection("drowsy_events")
                .where(filter=FieldFilter("device_id", "==", device_id))
                .order_by("timestamp", direction="DESCENDING")
                .limit(50)
                .stream()
            )

            for doc in docs:
                event = doc.to_dict()
                event["id"] = doc.id
                events.append(event)
        except Exception:
            # Fallback: get all events and filter in code
            print("Using fallback query for history")
            docs = db.collection("drowsy_events").limit(200).stream()

            for doc in docs:
                event = doc.to_dict()
                if event.get("device_id") == device_id:
                    event["id"] = doc.id
                    events.append(event)

            # Sort by timestamp descending
            events.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
            events = events[:50]

    except Exception as e:
        print(f"Error fetching drowsiness history: {e}")
        import traceback

        traceback.print_exc()
        events = []

    # Calculate today's events
    today = date.today()
    today_events = 0
    for event in events:
        if event.get("timestamp"):
            event_date = event["timestamp"]
            if isinstance(event_date, datetime):
                if event_date.date() == today:
                    today_events += 1
            elif isinstance(event_date, date):
                if event_date == today:
                    today_events += 1

    return render_template(
        "drowsiness_history.html",
        device_id=device_id,
        events=events,
        today_events=today_events,
    )


# ===============================
# Session History Page (RTDB)
# ===============================
@dashboard_bp.route("/sessions")
def session_history():
    device_id = current_app.config["DEVICE_ID"]

    try:
        # ✅ Already normalized sessions
        sessions = get_rtdb_sessions(device_id)

        # Sort latest first
        sessions.sort(
            key=lambda s: s.get("start_time"),
            reverse=True
        )

        sessions = sessions[:20]
        total_hours = get_total_worked_hours(device_id)

    except Exception as e:
        print("Sessions error:", e)
        import traceback
        traceback.print_exc()
        sessions = []
        total_hours = 0.0

    return render_template(
            "sessions.html",
            device_id=device_id,
            sessions=sessions,
            total_hours=total_hours,
            now=datetime.now(timezone.utc)
        )

