"""
Deprecated module.

All old Firestore-based session tracking logic has been removed.
Sessions are now maintained directly by the ESP32 into Firebase
Realtime Database under:

    /devices/{device_id}/history

This file is kept only to avoid import errors from any legacy code.
New code MUST NOT depend on this module.
"""
