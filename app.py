# backend/app.py

from flask import Flask
from services.firebase import init_firebase
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.worker import worker_bp
import os
import threading
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)

    # ===============================
    # Config
    # ===============================
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["DEVICE_ID"] = os.getenv("DEVICE_ID", "helmet_01")

    # ===============================
    # Firebase Init
    # ===============================
    init_firebase()

    # ===============================
    # Register Blueprints
    # ===============================
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(worker_bp)

    # ===============================
    # Health Check
    # ===============================
    @app.route("/health")
    def health():
        return {
            "status": "RUNNING",
            "service": "Drowsiness Detection Backend",
            "firebase": "CONNECTED"
        }

    return app


app = create_app()

# ===============================
# Background Session Tracker
# ===============================
def track_sessions():
    """
    Background thread to track device sessions
    """
    from services.session_tracker import check_and_update_sessions
    
    while True:
        try:
            device_id = app.config["DEVICE_ID"]
            check_and_update_sessions(device_id)
        except Exception as e:
            print(f"Error in session tracker: {e}")
        time.sleep(30)  # Check every 30 seconds

# Start background thread
session_thread = threading.Thread(target=track_sessions, daemon=True)
session_thread.start()

# ===============================
# Render / Local Run
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
