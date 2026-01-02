# backend/routes/dashboard.py

from flask import Blueprint, render_template, current_app
from services.firebase import get_live_ref, get_firestore, safe_get
from services.alerts import get_recent_alerts
from services.work_hours import get_total_worked_hours
from google.api_core import exceptions as google_exceptions

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
        worked_hours=worked_hours
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
            docs = db.collection("drowsy_events") \
                     .where(filter=FieldFilter("device_id", "==", device_id)) \
                     .order_by("timestamp", direction="DESCENDING") \
                     .limit(50) \
                     .stream()
            
            for doc in docs:
                event = doc.to_dict()
                event["id"] = doc.id
                events.append(event)
        except:
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
        today_events=today_events
    )


# ===============================
# Session History Page
# ===============================
@dashboard_bp.route("/sessions")
def session_history():
    device_id = current_app.config["DEVICE_ID"]

    try:
        db = get_firestore()
        from datetime import datetime

        sessions = []

        # Always scan all documents to ensure we get all data
        print(f"Fetching sessions for device_id: {device_id}")
        try:
            # Get all sessions and filter in Python
            docs = db.collection("sessions").stream()
            
            doc_count = 0
            for doc in docs:
                doc_count += 1
                s = doc.to_dict()
                doc_device_id = s.get("device_id")
                
                # Debug: print first few documents
                if doc_count <= 3:
                    print(f"  Doc {doc_count}: device_id='{doc_device_id}', start_time={s.get('start_time')}")
                
                if doc_device_id == device_id:
                    s["id"] = doc.id
                    sessions.append(s)
                    print(f"  ✓ Found matching session: {doc.id}")

            print(f"Total documents scanned: {doc_count}, Matching sessions: {len(sessions)}")

            # Sort by start_time in Python (descending)
            sessions.sort(
                key=lambda x: x.get("start_time") if x.get("start_time") else datetime.min,
                reverse=True,
            )

            # Keep only 20 latest
            sessions = sessions[:20]
            
            # Convert Firestore Timestamps to Python datetime objects for template
            current_time = datetime.utcnow()
            total_hours = 0.0
            
            for s in sessions:
                try:
                    start = s.get("start_time")
                    end = s.get("end_time")
                    
                    # Convert Firestore Timestamp to datetime if needed
                    if start:
                        if hasattr(start, 'timestamp'):
                            # Firestore Timestamp object
                            start = datetime.fromtimestamp(start.timestamp())
                        elif not isinstance(start, datetime):
                            # Try to convert if it's a different type
                            try:
                                if hasattr(start, 'replace'):
                                    pass  # Already datetime
                                else:
                                    continue  # Skip if we can't convert
                            except:
                                continue
                        
                        # Store converted datetime back
                        s["start_time"] = start
                        
                        if end:
                            # Convert Firestore Timestamp to datetime if needed
                            if hasattr(end, 'timestamp'):
                                end = datetime.fromtimestamp(end.timestamp())
                            elif not isinstance(end, datetime):
                                try:
                                    if hasattr(end, 'replace'):
                                        pass  # Already datetime
                                    else:
                                        end = None  # Can't convert, treat as None
                                except:
                                    end = None
                            
                            if end:
                                s["end_time"] = end
                                duration = (end - start).total_seconds() / 3600
                            else:
                                s["end_time"] = None
                                # Old session without end_time
                                time_since_start = current_time - start
                                if time_since_start.total_seconds() > 3600:
                                    duration = 1.0
                                else:
                                    duration = time_since_start.total_seconds() / 3600
                        else:
                            s["end_time"] = None
                            # Session without end_time
                            time_since_start = current_time - start
                            if time_since_start.total_seconds() > 3600:
                                duration = 1.0
                            else:
                                duration = time_since_start.total_seconds() / 3600
                        
                        if duration > 0:
                            total_hours += duration
                except Exception as e:
                    print(f"Error processing session {s.get('id', 'unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Set defaults to prevent template errors
                    if "start_time" not in s or not isinstance(s.get("start_time"), datetime):
                        s["start_time"] = None
                    if "end_time" not in s:
                        s["end_time"] = None
                    continue
        except Exception as e:
            print(f"Error fetching sessions: {e}")
            import traceback
            traceback.print_exc()
            sessions = []
            total_hours = 0.0
    except Exception as e:
        print(f"Error in session_history route: {e}")
        import traceback
        traceback.print_exc()
        sessions = []
        total_hours = 0.0

    from datetime import datetime
    current_time = datetime.utcnow()
    return render_template(
        "sessions.html",
        device_id=device_id,
        sessions=sessions,
        total_hours=total_hours,
        now=current_time
    )

