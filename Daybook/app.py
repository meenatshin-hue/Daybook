"""Daybook: a month calendar with color-coded reminders and a to-do list for every day.

Run with:  streamlit run app.py
"""

import calendar
import html
import secrets
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

import db
import notifier

st.set_page_config(page_title="Daybook", page_icon="🗓️", layout="wide")
db.init()
notifier.start()

EMOJIS = ["⏰", "📌", "💊", "🎂", "📚", "💼", "🏋️", "🛒", "📞", "✈️", "🍽️", "💡", "❤️", "🎉", "🐶", "🧹"]
GREEN, RED = "#15803d", "#d1343a"

# ---------- styles: white background, black text, green/red buttons ----------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,800&display=swap');

.block-container {{ padding-top: 2rem; max-width: 1300px; }}
.month {{ font-family: "Bricolage Grotesque", system-ui, sans-serif; font-size: clamp(38px, 6vw, 64px);
  font-weight: 800; letter-spacing: -0.03em; line-height: 1; color: #111; }}
.month span {{ font-weight: 400; color: #686868; }}
.now {{ color: #686868; font-size: 14px; font-variant-numeric: tabular-nums; }}
.now b {{ color: #111; }}
.dow {{ font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #686868;
  border-bottom: 1.5px solid #111; padding-bottom: 6px; }}
.panel-title {{ font-family: "Bricolage Grotesque", system-ui, sans-serif; font-size: 28px; font-weight: 800;
  letter-spacing: -0.02em; line-height: 1.1; color: #111; }}
.sub {{ color: #686868; font-size: 13px; }}

/* Buttons: green = go / add / save, red = back / remove / delete */
button[kind="primary"], button[kind="primaryFormSubmit"] {{ background: {GREEN} !important; border: 1.5px solid {GREEN} !important; color: #fff !important; }}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {{ background: #116a32 !important; border-color: #116a32 !important; }}
button[kind="secondary"], button[kind="secondaryFormSubmit"] {{ background: #fff !important; border: 1.5px solid {RED} !important; color: {RED} !important; }}
button[kind="secondary"]:hover {{ background: #fdeced !important; }}
[class*="st-key-go-"] button {{ border-color: {GREEN} !important; color: {GREEN} !important; }}
[class*="st-key-go-"] button:hover {{ background: #e9f6ee !important; }}

/* Calendar grid */
.st-key-calgrid [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 4px !important; }}
.st-key-calgrid [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; }}
[class*="st-key-cell"] {{ min-height: 128px; padding: 6px !important; gap: 4px !important; border-radius: 6px !important; }}
[class*="st-key-cell"][class*="_s-"] {{ border: 2px solid #111 !important; }}
[class*="st-key-cell"][class*="_o"] {{ opacity: .45; }}
[class*="st-key-day-"] button {{ min-height: 30px; height: 30px; width: 30px; padding: 0 !important; border-radius: 50%;
  color: #111 !important; font-weight: 700; }}
[class*="st-key-cell_t"] [class*="st-key-day-"] button {{ background: #111 !important; color: #fff !important; }}
[class*="st-key-todo"] button {{ min-height: 28px !important; height: 28px; width: 28px; padding: 0 !important; border-radius: 50% !important;
  font-size: 14px; }}
[class*="st-key-todo-"] button {{ background: #fff !important; color: {GREEN} !important; }}
.chip {{ display: block; font-size: 12px; font-weight: 500; border-radius: 4px; padding: 1px 6px; margin-bottom: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.more {{ font-size: 11px; color: #686868; }}
@media (max-width: 700px) {{
  [class*="st-key-cell"] {{ min-height: 80px; padding: 2px !important; }}
  .chip .t {{ display: none; }}
  .chip {{ display: inline-block; padding: 0 2px; margin-right: 2px; }}
  [class*="st-key-day-"] button {{ width: 24px; height: 24px; min-height: 24px; font-size: 12px; }}
  [class*="st-key-todo"] button {{ width: 22px; height: 22px; min-height: 22px !important; font-size: 11px; }}
}}

/* Reminder rows */
.rem {{ display: flex; gap: 10px; align-items: flex-start; }}
.rem-emoji {{ width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center; font-size: 18px; flex: none; }}
.rem-title {{ font-weight: 600; color: #111; }}
.rem-meta {{ font-size: 13px; color: #686868; }}
.tag {{ font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 999px; margin-left: 6px; }}

.smiley {{ text-align: center; font-size: 80px; line-height: 1.1; }}
.smiley-text {{ text-align: center; font-weight: 600; font-size: 18px; margin-bottom: 8px; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- helpers ----------

def fmt_time(t):
    return t.strftime("%I:%M %p").lstrip("0")


def long_date(d):
    return f"{d:%A, %B} {d.day}"


def text_on(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lum = sum(w * (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4) for w, c in zip((0.2126, 0.7152, 0.0722), (r, g, b)))
    return "#111111" if lum > 0.4 else "#ffffff"


def tint(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def next_hour():
    return (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0).time()


def flash(kind, text):
    st.session_state.flash.append((kind, text))


# ---------- session state ----------

ss = st.session_state
today = date.today()
ss.setdefault("page", "calendar")
ss.setdefault("cursor", (today.year, today.month))
ss.setdefault("selected", today)
ss.setdefault("todo_date", today)
ss.setdefault("open_list", None)
ss.setdefault("confirm_delete", None)
ss.setdefault("toasted", set())
ss.setdefault("flash", [])
ss.setdefault("rf_title", "")
ss.setdefault("rf_date", today)
ss.setdefault("rf_time", next_hour())
ss.setdefault("rf_label", "")
ss.setdefault("rf_color", "#1E88E5")
ss.setdefault("rf_emoji", "⏰")
ss.setdefault("topic_input", db.get_setting("ntfy_topic", "") or f"daybook-{secrets.token_hex(4)}")


# ---------- callbacks ----------

def shift_month(delta):
    y, m = ss.cursor
    m += delta
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    ss.cursor = (y, m)


def go_today():
    t = date.today()
    ss.cursor = (t.year, t.month)
    select_day(t)


def select_day(d):
    ss.selected = d
    ss.cursor = (d.year, d.month)
    ss.rf_date = d


def open_todo(d):
    ss.todo_date = d
    ss.open_list = None
    ss.confirm_delete = None
    ss.page = "todo"


def go_calendar():
    ss.page = "calendar"


def add_reminder():
    title = ss.rf_title.strip()
    if not title:
        flash("warn", "Give the reminder a title first.")
        return
    db.add_reminder(title, ss.rf_date, ss.rf_time, ss.rf_label.strip(), ss.rf_color, ss.rf_emoji or "")
    select_day(ss.rf_date)
    ss.rf_title = ""
    ss.rf_label = ""
    flash("ok", f"Reminder set for {long_date(ss.rf_date)} at {fmt_time(ss.rf_time)}.")


def remove_reminder(rid):
    db.delete_reminder(rid)


def create_list():
    name = ss.new_list_name.strip()
    if not name:
        flash("warn", "Give the list a name first.")
        return
    ss.open_list = db.create_list(name, ss.todo_date)
    ss.new_list_name = ""


def add_item():
    text = ss.new_item_text.strip()
    if text and ss.open_list:
        db.add_item(ss.open_list, text)
    ss.new_item_text = ""


def toggle_item(item_id):
    db.set_item_done(item_id, ss[f"item-{item_id}"])


def open_list(list_id, day=None):
    ss.open_list = list_id
    ss.confirm_delete = None
    if day:
        ss.todo_date = day


def delete_list(list_id):
    db.delete_list(list_id)
    ss.open_list = None
    ss.confirm_delete = None


def save_topic():
    topic = ss.topic_input.strip()
    db.set_setting("ntfy_topic", topic)
    flash("ok", "Phone notifications are on." if topic else "Phone notifications are off.")


def send_test():
    topic = db.get_setting("ntfy_topic", "")
    if not topic:
        flash("warn", "Save a topic name first.")
    elif notifier.send(topic, "⏰ Daybook test", "Phone notifications are working."):
        flash("ok", "Test sent. Check your phone.")
    else:
        flash("warn", "The test didn't go through. Check your internet connection and try again.")


# ---------- sidebar: phone notifications ----------

with st.sidebar:
    st.subheader("📱 Phone notifications")
    saved_topic = db.get_setting("ntfy_topic", "")
    if saved_topic:
        st.success("On. Reminders are sent to your phone when they're due.")
    else:
        st.info("Off. Follow the steps below to turn them on.")
    st.markdown(
        "1. Install the free **ntfy** app on your phone (App Store or Google Play).\n"
        "2. In the app, tap **+** and subscribe to the topic name below.\n"
        "3. Press **Save** here, then **Send test notification**."
    )
    st.text_input("Topic name", key="topic_input", max_chars=64)
    st.button("Save", type="primary", on_click=save_topic, width="stretch")
    st.button("Send test notification", key="go-test", on_click=send_test, width="stretch")
    st.caption(
        "Anyone who knows the topic name can see these notifications, so keep it hard to guess. "
        "Notifications go out only while Daybook is running on this computer."
    )

for kind, text in ss.flash:
    st.toast(text, icon="✅" if kind == "ok" else "⚠️")
ss.flash = []


# ---------- live clock + due-reminder toasts ----------

@st.fragment(run_every="30s")
def live_strip():
    now = datetime.now().astimezone()
    st.markdown(
        f'<div class="now"><b>{html.escape(long_date(now))}</b> · {fmt_time(now)} · {html.escape(now.tzname() or "")}</div>',
        unsafe_allow_html=True,
    )
    naive_now = now.replace(tzinfo=None)
    for r in db.reminders_between(naive_now.date() - timedelta(days=1), naive_now.date()):
        if r["id"] in ss.toasted:
            continue
        if timedelta(0) <= naive_now - r["due"] <= timedelta(hours=1):
            ss.toasted.add(r["id"])
            st.toast(f"**{r['title']}** · {fmt_time(r['due'])}", icon=r["emoji"] or "⏰")


# ---------- calendar page ----------

def render_cell(d, month, rems, list_summary):
    k = d.isoformat()
    flags = ("_t" if d == date.today() else "") + ("_s" if d == ss.selected else "") + ("_o" if d.month != month else "")
    total_lists, all_done = list_summary.get(d, (0, False))
    with st.container(border=True, key=f"cell{flags}-{k}"):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", gap="small"):
            st.button(str(d.day), key=f"day-{k}", type="tertiary", on_click=select_day, args=(d,),
                      help=long_date(d))
            st.button("😊" if all_done else "✓", key=f"todo{'h' if total_lists else ''}-{k}", type="primary",
                      on_click=open_todo, args=(d,), help=f"To-do lists for {d:%B} {d.day}")
        if rems:
            chips = []
            for r in rems[:3]:
                chips.append(
                    f'<span class="chip" style="background:{r["color"]};color:{text_on(r["color"])}" '
                    f'title="{html.escape(fmt_time(r["due"]) + " " + r["title"])}">{html.escape(r["emoji"])}'
                    f'<span class="t"> {html.escape(fmt_time(r["due"]))} {html.escape(r["title"])}</span></span>'
                )
            if len(rems) > 3:
                chips.append(f'<div class="more">+{len(rems) - 3} more</div>')
            st.markdown("".join(chips), unsafe_allow_html=True)


def render_grid():
    y, m = ss.cursor
    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(y, m)
    start, end = weeks[0][0], weeks[-1][-1]
    by_day = {}
    for r in db.reminders_between(start, end):
        by_day.setdefault(r["due"].date(), []).append(r)
    list_summary = {}
    for l in db.lists_between(start, end):
        d = date.fromisoformat(l["day"])
        count, done = list_summary.get(d, (0, True))
        list_summary[d] = (count + 1, done and l["total"] > 0 and l["finished"] == l["total"])

    with st.container(key="calgrid"):
        header = st.columns(7)
        for col, name in zip(header, ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            col.markdown(f'<div class="dow">{name}</div>', unsafe_allow_html=True)
        for week in weeks:
            for col, d in zip(st.columns(7), week):
                with col:
                    render_cell(d, m, by_day.get(d, []), list_summary)


def render_panel():
    d = ss.selected
    rems = [r for r in db.reminders_between(d, d)]
    lists = db.lists_between(d, d)
    st.markdown(f'<div class="panel-title">{html.escape(long_date(d))}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub">{len(rems)} reminder{"s" if len(rems) != 1 else ""} · '
        f'{len(lists)} to-do list{"s" if len(lists) != 1 else ""}</div>',
        unsafe_allow_html=True,
    )
    st.button("✓  To-do lists for this day", key="open-todo-panel", type="primary", on_click=open_todo, args=(d,),
              width="stretch")

    st.markdown("**Reminders**")
    if not rems:
        st.caption("Nothing scheduled. Add a reminder below.")
    now = datetime.now()
    for r in rems:
        with st.container(border=True, key=f"rem-{r['id']}"):
            label = (
                f'<span class="tag" style="background:{r["color"]};color:{text_on(r["color"])}">{html.escape(r["label"])}</span>'
                if r["label"] else ""
            )
            past = " (past)" if r["due"] < now else ""
            st.markdown(
                f'<div class="rem"><div class="rem-emoji" style="background:{tint(r["color"], 0.2)}">{html.escape(r["emoji"] or "⏰")}</div>'
                f'<div><div class="rem-title">{html.escape(r["title"])}</div>'
                f'<div class="rem-meta">{fmt_time(r["due"])}{past}{label}</div></div></div>',
                unsafe_allow_html=True,
            )
            st.button("Remove", key=f"delrem-{r['id']}", on_click=remove_reminder, args=(r["id"],))

    st.markdown("**New reminder**")
    with st.form("reminder_form", border=True):
        st.text_input("What should we remind you about?", key="rf_title", placeholder="Call the dentist", max_chars=120)
        c1, c2 = st.columns(2)
        c1.date_input("Date", key="rf_date")
        c2.time_input("Time", key="rf_time", step=300)
        st.text_input("Label", key="rf_label", placeholder="Health, School, Work…", max_chars=30)
        st.color_picker("Color", key="rf_color")
        st.pills("Emoji", EMOJIS, key="rf_emoji")
        st.form_submit_button("Add reminder", type="primary", on_click=add_reminder)


def calendar_page():
    y, m = ss.cursor
    top_l, top_r = st.columns([3, 2], vertical_alignment="bottom")
    with top_l:
        st.markdown(f'<div class="month">{calendar.month_name[m]} <span>{y}</span></div>', unsafe_allow_html=True)
        live_strip()
    with top_r:
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("← Prev", key="go-prev", on_click=shift_month, args=(-1,))
            st.button("Today", key="today", type="primary", on_click=go_today)
            st.button("Next →", key="go-next", on_click=shift_month, args=(1,))

    left, right = st.columns([3, 1.25], gap="large")
    with left:
        render_grid()
    with right:
        render_panel()


# ---------- to-do page ----------

def todo_page():
    d = ss.todo_date
    st.button("← Back to calendar", key="back", on_click=go_calendar)
    st.markdown(f'<div class="month" style="font-size:44px">To-do lists <span>· {html.escape(long_date(d))}</span></div>',
                unsafe_allow_html=True)
    live_strip()

    lists = db.lists_between(d, d)
    ids = [l["id"] for l in lists]
    if ss.open_list is not None and db.get_list(ss.open_list) is None:
        ss.open_list = None
    if ss.open_list is None and lists:
        ss.open_list = ids[-1]

    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown("**Create a to-do list**")
        with st.form("new_list_form", border=False):
            st.text_input("List name", key="new_list_name", placeholder="Groceries", max_chars=80)
            st.form_submit_button("Create list", type="primary", on_click=create_list)
        st.markdown("**Lists for this day**")
        if not lists:
            st.caption("No lists yet. Create one above.")
        for l in lists:
            done = l["total"] > 0 and l["finished"] == l["total"]
            label = f"{'😊 ' if done else ''}{l['name']}  ·  {l['finished']}/{l['total']}"
            is_open = l["id"] == ss.open_list
            st.button(label, key=f"{'openlist' if is_open else 'go-openlist'}-{l['id']}",
                      type="primary" if is_open else "secondary", on_click=open_list, args=(l["id"],), width="stretch")

    with right:
        current = db.get_list(ss.open_list) if ss.open_list else None
        if current is None:
            with st.container(border=True):
                st.markdown("#### No list open")
                st.caption("Name a list on the left and press Create list. Add items, check them off, "
                           "and every list is saved for later.")
        else:
            items = db.list_items(current["id"])
            total, finished = len(items), sum(i["done"] for i in items)
            with st.container(border=True):
                with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                    st.markdown(f"### {current['name']}")
                    if ss.confirm_delete == current["id"]:
                        with st.container(horizontal=True, horizontal_alignment="right"):
                            st.button("Delete", key="confirm-del", on_click=delete_list, args=(current["id"],))
                            st.button("Keep", key="go-keep", on_click=lambda: ss.update(confirm_delete=None))
                    else:
                        st.button("Delete list", key="ask-del", on_click=lambda: ss.update(confirm_delete=current["id"]))
                st.progress(finished / total if total else 0.0, text=f"{finished} of {total} item{'s' if total != 1 else ''} done")
                if total and finished == total:
                    st.markdown('<div class="smiley">😊</div><div class="smiley-text">Everything\'s done. Nice work!</div>',
                                unsafe_allow_html=True)
                for it in items:
                    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                        st.checkbox(it["text"], value=bool(it["done"]), key=f"item-{it['id']}",
                                    on_change=toggle_item, args=(it["id"],))
                        st.button("✕", key=f"delitem-{it['id']}", on_click=db.delete_item, args=(it["id"],),
                                  help="Remove item")
                with st.form("add_item_form", border=False):
                    st.text_input("New item", key="new_item_text", placeholder="Add an item", max_chars=160)
                    st.form_submit_button("Add item", type="primary", on_click=add_item)

    st.divider()
    st.markdown("**All saved lists**")
    saved = db.all_lists_with_items()
    if not saved:
        st.caption("Lists you create on any day are saved here with their items and progress.")
        return
    table = pd.DataFrame(
        {
            "List": [l["name"] for l in saved],
            "Date": [date.fromisoformat(l["day"]).strftime("%b %d, %Y") for l in saved],
            "Items": [", ".join(l["items"]) or "No items yet" for l in saved],
            "Finished": [f"{l['finished']}/{l['total']}" + (" 😊" if l["total"] and l["finished"] == l["total"] else "")
                         for l in saved],
        }
    )
    saved_ids = [(l["id"], date.fromisoformat(l["day"])) for l in saved]

    def open_from_table():
        rows = ss.archive.selection.rows
        if rows:
            open_list(*saved_ids[rows[0]])

    st.caption("Select a row to open that list.")
    st.dataframe(table, hide_index=True, key="archive", on_select=open_from_table, selection_mode="single-row")


if ss.page == "todo":
    todo_page()
else:
    calendar_page()
