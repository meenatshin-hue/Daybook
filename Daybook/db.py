"""Supabase storage for Daybook: reminders, to-do lists, their items, and settings.

Connects with the project URL and publishable key, read from the SUPABASE_URL and SUPABASE_KEY
environment variables or from .streamlit/secrets.toml. The tables come from
supabase/migrations, which you run once in the Supabase SQL Editor.
"""

import os
import threading
from datetime import date, datetime, time

from postgrest import APIError
from supabase import create_client

SCHEMA_FILE = "supabase/migrations/20261012000000_daybook_schema.sql"
ACCESS_FILE = "supabase/migrations/20261012000100_allow_publishable_key.sql"

_client = None
_client_lock = threading.Lock()
_initialized = False


def _secret(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets[name]
    except Exception:
        raise RuntimeError(
            f"{name} is not set. Add it to .streamlit/secrets.toml "
            "(see .streamlit/secrets.toml.example) or set it as an environment variable."
        ) from None


def client():
    global _client
    with _client_lock:
        if _client is None:
            _client = create_client(_secret("SUPABASE_URL"), _secret("SUPABASE_KEY"))
    return _client


def _table(name):
    return client().table(name)


def init():
    """Check once per process that the tables exist and the key can write to them."""
    global _initialized
    if _initialized:
        return
    try:
        for name in ("reminders", "todo_lists", "todo_items", "settings"):
            _table(name).select("*").limit(1).execute()
        _table("settings").upsert({"key": "_access_check", "value": "ok"}).execute()
        _table("settings").delete().eq("key", "_access_check").execute()
    except APIError as e:
        if e.code in ("PGRST205", "42P01"):
            raise RuntimeError(
                f"Daybook's tables aren't in Supabase yet. Open your project's SQL Editor, "
                f"paste in {SCHEMA_FILE}, and press Run."
            ) from e
        if e.code == "42501":
            raise RuntimeError(
                f"Your key isn't allowed to change Daybook's tables yet. Open your project's SQL Editor, "
                f"paste in {ACCESS_FILE}, and press Run."
            ) from e
        raise
    _initialized = True


def _all_rows(make_query, page=1000):
    """Fetch every row; Supabase returns at most 1000 per request."""
    rows, start = [], 0
    while True:
        batch = make_query().range(start, start + page - 1).execute().data
        rows += batch
        if len(batch) < page:
            return rows
        start += page


def _reminder(row):
    r = dict(row)
    r["at"] = r["at"][:5]  # "HH:MM:SS" -> "HH:MM"
    r["due"] = datetime.fromisoformat(f"{r['day']}T{r['at']}")
    return r


# ---------- reminders ----------

def add_reminder(title, day: date, at: time, label, color, emoji):
    _table("reminders").insert({
        "title": title, "day": day.isoformat(), "at": at.strftime("%H:%M"),
        "label": label, "color": color, "emoji": emoji or "",
    }).execute()


def delete_reminder(reminder_id):
    _table("reminders").delete().eq("id", reminder_id).execute()


def reminders_between(start: date, end: date):
    rows = (_table("reminders").select("*")
            .gte("day", start.isoformat()).lte("day", end.isoformat())
            .order("day").order("at").execute().data)
    return [_reminder(r) for r in rows]


def unnotified_reminders():
    rows = _table("reminders").select("*").eq("notified", False).execute().data
    return [_reminder(r) for r in rows]


def mark_notified(reminder_id):
    _table("reminders").update({"notified": True}).eq("id", reminder_id).execute()


# ---------- to-do lists ----------

_LIST_COLUMNS = "id,name,day,created,todo_items(id,text,done)"


def _list(row, with_items=False):
    l = dict(row)
    items = sorted(l.pop("todo_items") or [], key=lambda i: i["id"])
    l["total"] = len(items)
    l["finished"] = sum(1 for i in items if i["done"])
    if with_items:
        l["items"] = [i["text"] for i in items]
    return l


def create_list(name, day: date):
    rows = _table("todo_lists").insert({"name": name, "day": day.isoformat()}).execute().data
    return rows[0]["id"]


def delete_list(list_id):
    _table("todo_lists").delete().eq("id", list_id).execute()


def get_list(list_id):
    rows = _table("todo_lists").select(_LIST_COLUMNS).eq("id", list_id).execute().data
    return _list(rows[0]) if rows else None


def lists_between(start: date, end: date):
    rows = (_table("todo_lists").select(_LIST_COLUMNS)
            .gte("day", start.isoformat()).lte("day", end.isoformat())
            .order("day").order("id").execute().data)
    return [_list(r) for r in rows]


def all_lists_with_items():
    """Every saved list with its name, date, items contained, and items finished."""
    rows = _all_rows(lambda: _table("todo_lists").select(_LIST_COLUMNS)
                     .order("day", desc=True).order("id", desc=True))
    return [_list(r, with_items=True) for r in rows]


def list_items(list_id):
    return _table("todo_items").select("*").eq("list_id", list_id).order("id").execute().data


def add_item(list_id, text):
    _table("todo_items").insert({"list_id": list_id, "text": text}).execute()


def set_item_done(item_id, done: bool):
    _table("todo_items").update({"done": bool(done)}).eq("id", item_id).execute()


def delete_item(item_id):
    _table("todo_items").delete().eq("id", item_id).execute()


# ---------- settings ----------

def get_setting(key, default=""):
    rows = _table("settings").select("value").eq("key", key).execute().data
    return rows[0]["value"] if rows else default


def set_setting(key, value):
    _table("settings").upsert({"key": key, "value": value}).execute()
