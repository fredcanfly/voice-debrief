-- Enable RLS
alter table profiles enable row level security;
alter table user_settings enable row level security;
alter table debrief_sessions enable row level security;
alter table debrief_turns enable row level security;
alter table usage_monthly enable row level security;

-- Profiles
create policy if not exists profiles_select_own on profiles
for select using (auth.uid() = id);

create policy if not exists profiles_insert_own on profiles
for insert with check (auth.uid() = id);

create policy if not exists profiles_update_own on profiles
for update using (auth.uid() = id);

-- User settings
create policy if not exists settings_select_own on user_settings
for select using (auth.uid() = user_id);

create policy if not exists settings_insert_own on user_settings
for insert with check (auth.uid() = user_id);

create policy if not exists settings_update_own on user_settings
for update using (auth.uid() = user_id);

-- Debrief sessions
create policy if not exists sessions_select_own on debrief_sessions
for select using (auth.uid() = user_id);

create policy if not exists sessions_insert_own on debrief_sessions
for insert with check (auth.uid() = user_id);

create policy if not exists sessions_update_own on debrief_sessions
for update using (auth.uid() = user_id);

create policy if not exists sessions_delete_own on debrief_sessions
for delete using (auth.uid() = user_id);

-- Debrief turns
create policy if not exists turns_select_own on debrief_turns
for select using (auth.uid() = user_id);

create policy if not exists turns_insert_own on debrief_turns
for insert with check (auth.uid() = user_id);

create policy if not exists turns_update_own on debrief_turns
for update using (auth.uid() = user_id);

create policy if not exists turns_delete_own on debrief_turns
for delete using (auth.uid() = user_id);

-- Usage
create policy if not exists usage_select_own on usage_monthly
for select using (auth.uid() = user_id);

create policy if not exists usage_insert_own on usage_monthly
for insert with check (auth.uid() = user_id);

create policy if not exists usage_update_own on usage_monthly
for update using (auth.uid() = user_id);

-- Storage bucket policies (bucket must exist: debrief-files)
create policy if not exists "debrief-files read own" on storage.objects
for select using (bucket_id = 'debrief-files' and owner = auth.uid());

create policy if not exists "debrief-files write own" on storage.objects
for insert with check (bucket_id = 'debrief-files' and owner = auth.uid());

create policy if not exists "debrief-files update own" on storage.objects
for update using (bucket_id = 'debrief-files' and owner = auth.uid());

create policy if not exists "debrief-files delete own" on storage.objects
for delete using (bucket_id = 'debrief-files' and owner = auth.uid());
