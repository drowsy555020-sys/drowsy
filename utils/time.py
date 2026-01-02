from datetime import datetime, timezone

def utcnow():
    """
    Always return timezone-aware UTC datetime
    """
    return datetime.now(timezone.utc)
