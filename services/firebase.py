# backend/services/firebase.py

import os
import firebase_admin
from firebase_admin import credentials, firestore, db

_firestore = None
_rtdb = None


def init_firebase():
    """
    Initialize Firebase Admin SDK
    Uses environment variables (Render safe)
    """
    global _firestore, _rtdb

    if firebase_admin._apps:
        return

    firebase_config = {
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
    }

    cred = credentials.Certificate(firebase_config)

    firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": os.getenv("FIREBASE_RTDB_URL")
        }
    )

    _firestore = firestore.client()
    _rtdb = db.reference()

    print("✅ Firebase initialized (Firestore + Realtime DB)")


# ===============================
# Firestore
# ===============================
def get_firestore():
    if not _firestore:
        raise RuntimeError("Firestore not initialized")
    return _firestore


# ===============================
# Realtime Database
# ===============================
def get_rtdb():
    if not _rtdb:
        raise RuntimeError("Realtime DB not initialized")
    return _rtdb


# ===============================
# Helpers
# ===============================
def get_device_ref(device_id):
    """
    /devices/{device_id}
    """
    return get_rtdb().child("devices").child(device_id)


def get_live_ref(device_id):
    """
    /devices/{device_id}/live
    """
    return get_device_ref(device_id).child("live")


def get_control_ref(device_id):
    """
    /devices/{device_id}/control
    """
    return get_device_ref(device_id).child("control")


# ===============================
# Safe Get Helper
# ===============================
def safe_get(ref, default=None):
    """
    Safely get data from Firebase Realtime Database.
    Returns default value if path doesn't exist (404 error).
    """
    try:
        data = ref.get()
        return data if data is not None else default
    except firebase_admin.exceptions.NotFoundError:
        return default
    except Exception as e:
        print(f"Warning: Error reading from Firebase: {e}")
        return default
