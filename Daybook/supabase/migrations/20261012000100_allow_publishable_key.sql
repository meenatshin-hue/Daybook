-- Let the project's publishable (anon) key read and write Daybook's tables.
-- Anyone holding the project URL and publishable key gets full access to this data, so keep both private.

grant select, insert, update, delete on public.reminders, public.todo_lists, public.todo_items, public.settings to anon;

drop policy if exists "daybook publishable key access" on public.reminders;
create policy "daybook publishable key access" on public.reminders for all to anon using (true) with check (true);

drop policy if exists "daybook publishable key access" on public.todo_lists;
create policy "daybook publishable key access" on public.todo_lists for all to anon using (true) with check (true);

drop policy if exists "daybook publishable key access" on public.todo_items;
create policy "daybook publishable key access" on public.todo_items for all to anon using (true) with check (true);

drop policy if exists "daybook publishable key access" on public.settings;
create policy "daybook publishable key access" on public.settings for all to anon using (true) with check (true);
