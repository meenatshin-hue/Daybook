# Daybook

A Streamlit calendar with color-coded emoji reminders and a to-do list for every day. Data is stored in Supabase (Postgres).

## Set up Supabase (once)

1. Create a free project at https://supabase.com/dashboard.
2. Open **SQL Editor** and run these two files, in order (paste all of each and press **Run**). Or with the Supabase CLI: `supabase link`, then `supabase db push`.
   - `supabase/migrations/20261012000000_daybook_schema.sql` creates the tables.
   - `supabase/migrations/20261012000100_allow_publishable_key.sql` lets your publishable key use them.
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in both values from your project's **Connect** panel:
   - `SUPABASE_URL`: your project URL, like `https://abcdefghijkl.supabase.co`
   - `SUPABASE_KEY`: the publishable key (`sb_publishable_...`, or the legacy `anon` key)

Anyone with your project URL and publishable key can read and change Daybook's data, so keep `secrets.toml` private.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

It opens in your browser at http://localhost:8501. To use it on your phone, connect the phone to the same Wi-Fi and open the "Network URL" that Streamlit prints.

## Move your old data

If you used Daybook before, your data is in `daybook.db`. Copy it to Supabase once:

```
python migrate_sqlite_to_supabase.py
```

It only copies into empty tables, so running it twice can't make duplicates.

## Phone notifications

1. Install the free **ntfy** app on your phone.
2. In the app, tap **+** and subscribe to the topic name shown in Daybook's sidebar.
3. Press **Save** in the sidebar, then **Send test notification**.

Notifications are sent only while `streamlit run app.py` is running on this computer.

## Files

- `app.py`: the app (calendar page and to-do page)
- `db.py`: Supabase storage (reminders, to-do lists, items, settings)
- `supabase/migrations/`: the database schema
- `migrate_sqlite_to_supabase.py`: one-time copy of old `daybook.db` data into Supabase
- `notifier.py`: background thread that pushes due reminders through ntfy
- `.streamlit/secrets.toml`: your Supabase URL and publishable key (keep it private)
- `.streamlit/config.toml`: white and black theme
