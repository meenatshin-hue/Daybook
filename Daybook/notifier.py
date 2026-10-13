"""Background thread that pushes due reminders to your phone through ntfy (https://ntfy.sh)."""

import threading
import time
from datetime import datetime, timedelta

import requests
import streamlit as st

import db

NTFY_SERVER = "https://ntfy.sh"
CHECK_EVERY_SECONDS = 20
# A reminder that came due while Daybook wasn't running is only sent if it's at most this late.
LATE_LIMIT = timedelta(hours=1)


def send(topic, title, message):
    """Publish one notification. Returns True if ntfy accepted it."""
    try:
        resp = requests.post(
            NTFY_SERVER,
            json={"topic": topic, "title": title, "message": message, "priority": 4},
            timeout=10,
        )
        return resp.ok
    except requests.RequestException:
        return False


def check_once():
    now = datetime.now()
    topic = db.get_setting("ntfy_topic", "")
    for r in db.unnotified_reminders():
        if r["due"] > now:
            continue
        if not topic or now - r["due"] > LATE_LIMIT:
            db.mark_notified(r["id"])
            continue
        title = f"{r['emoji']} {r['title']}".strip()
        message = r["due"].strftime("%I:%M %p").lstrip("0")
        if r["label"]:
            message += f" · {r['label']}"
        if send(topic, title, message):
            db.mark_notified(r["id"])


def _loop():
    while True:
        try:
            check_once()
        except Exception:
            pass
        time.sleep(CHECK_EVERY_SECONDS)


@st.cache_resource
def start():
    """Start one notifier thread for the whole Streamlit server."""
    thread = threading.Thread(target=_loop, name="daybook-notifier", daemon=True)
    thread.start()
    return thread
