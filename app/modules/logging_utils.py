import os

LOG_ENABLED = os.getenv("APP_LOGS", "").lower() in ("1", "true", "yes", "on")

def log(*args, **kwargs):
    if LOG_ENABLED:
        print(*args, **kwargs)
