"""One-time copy of your old daybook.db (SQLite) data into Supabase.

Run with:  python migrate_sqlite_to_supabase.py

It only runs while Daybook's Supabase tables are empty, so it can't copy anything twice.
"""

import sqlite3
from datetime import date
from pathlib import Path

import db

SQLITE_PATH = Path(__file__).with_name("daybook.db")


def main():
    if not SQLITE_PATH.exists():
        print(f"No {SQLITE_PATH.name} found, nothing to copy.")
        return
    db.init()
    for name in ("reminders", "todo_lists", "todo_items"):
        if db.client().table(name).select("id").limit(1).execute().data:
            print(f"Supabase already has data in {name}, so nothing was copied.")
            return

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    reminders = src.execute("SELECT * FROM reminders ORDER BY id").fetchall()
    lists = src.execute("SELECT * FROM todo_lists ORDER BY id").fetchall()
    items = src.execute("SELECT * FROM todo_items ORDER BY id").fetchall()
    settings = src.execute("SELECT * FROM settings").fetchall()
    src.close()

    if reminders:
        db.client().table("reminders").insert([
            {"title": r["title"], "day": r["day"], "at": r["at"], "label": r["label"], "color": r["color"],
             "emoji": r["emoji"], "notified": bool(r["notified"])}
            for r in reminders
        ]).execute()

    # Supabase gives each list a new id, so point the items at the new ids.
    new_list_id = {}
    for l in lists:
        new_list_id[l["id"]] = db.create_list(l["name"], date.fromisoformat(l["day"]))
    copied_items = [
        {"list_id": new_list_id[i["list_id"]], "text": i["text"], "done": bool(i["done"])}
        for i in items if i["list_id"] in new_list_id
    ]
    if copied_items:
        db.client().table("todo_items").insert(copied_items).execute()

    for s in settings:
        db.set_setting(s["key"], s["value"])

    print(f"Copied {len(reminders)} reminders, {len(lists)} lists, {len(copied_items)} items, {len(settings)} settings.")


if __name__ == "__main__":
    main()
