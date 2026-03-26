-- ============================================================
-- FreezeAC Supabase Schema  (v2 — OTP + anonymous bookings)
-- Run in Supabase SQL Editor: Dashboard → SQL Editor → New Query
-- ============================================================

-- ============================================================
-- profiles
-- Supports:
--   • Email/password users
--   • Phone OTP users (phone stored here + in auth.users)
--   • Email OTP (magic-link) users
-- The trigger handle_new_user fires on auth.users INSERT and
-- creates a profile row automatically for every signup method.
-- ============================================================

create table if not exists public.profiles (
  id         uuid        primary key references auth.users(id) on delete cascade,
  full_name  text        not null default '',
  phone      text        not null default '',   -- E.164 e.g. +971585793050
  role       text        not null default 'customer'
               check (role in ('customer', 'admin', 'technician')),
  avatar_url text        not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Policies
create policy "Profiles viewable by owner"
  on public.profiles for select using (auth.uid() = id);

create policy "Admins can view all profiles"
  on public.profiles for select using (
    exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'admin')
  );

create policy "Users can update own profile"
  on public.profiles for update using (auth.uid() = id);

create policy "Users can insert own profile"
  on public.profiles for insert with check (auth.uid() = id);

-- service_role bypass: our FastAPI backend (supabase_admin) uses service key,
-- which bypasses RLS — no extra policy needed for server-side inserts.


-- Trigger: auto-create profile for EVERY auth method (password, OTP, magic-link)
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, full_name, phone)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    coalesce(new.phone, '')
  )
  on conflict (id) do nothing;   -- safe to re-run
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- ============================================================
-- bookings
-- user_id is nullable to support anonymous (walk-in / UI) bookings.
-- services stores the full cart as JSONB for multi-service orders.
-- ============================================================

create table public.bookings (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        references public.profiles(id) on delete set null,  -- nullable = anonymous OK
  service     text        not null default '',          -- human-readable label (first service or joined)
  services    jsonb       not null default '[]',        -- full cart: [{serviceId, qty, title, price}]
  amount      numeric(10,2) not null default 0,
  status      text        not null default 'pending'
                check (status in ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled')),
  scheduled_at timestamptz,
  address     text        default '',
  building    text        default '',                   -- flat / villa / tower
  name        text        default '',                   -- customer name (anonymous bookings)
  phone       text        default '',                   -- customer phone (anonymous bookings)
  notes       text        default '',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table public.bookings enable row level security;

create policy "Users can view own bookings"
  on public.bookings for select using (auth.uid() = user_id);

create policy "Users can create own bookings"
  on public.bookings for insert with check (auth.uid() = user_id);

create policy "Users can update own bookings"
  on public.bookings for update using (auth.uid() = user_id);

create policy "Admins can view all bookings"
  on public.bookings for select using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );

create policy "Admins can update all bookings"
  on public.bookings for update using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );


-- ============================================================
-- payments
-- user_id is nullable to support anonymous bookings.
-- provider = 'ziina' by default (UAE payment gateway).
-- ============================================================

create table public.payments (
  id           uuid        primary key default gen_random_uuid(),
  user_id      uuid        references public.profiles(id) on delete set null,  -- nullable
  booking_id   uuid        references public.bookings(id) on delete set null,
  amount       numeric(10,2) not null,
  currency     text        not null default 'AED',
  provider     text        not null default 'ziina',
  provider_ref text        default '',   -- Ziina payment_intent_id
  status       text        not null default 'pending'
                 check (status in ('pending', 'completed', 'failed', 'refunded')),
  created_at   timestamptz not null default now()
);

alter table public.payments enable row level security;

create policy "Users can view own payments"
  on public.payments for select using (auth.uid() = user_id);

create policy "Users can create own payments"
  on public.payments for insert with check (auth.uid() = user_id);

create policy "Admins can view all payments"
  on public.payments for select using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );


-- ============================================================
-- blog_posts
-- ============================================================

create table public.blog_posts (
  id               uuid    primary key default gen_random_uuid(),
  slug             text    unique not null,
  title            text    not null,
  excerpt          text    not null default '',
  content          text    not null default '',
  cover_image      text    default '',
  author_id        uuid    references public.profiles(id) on delete set null,
  published        boolean not null default false,
  tags             text[]  default '{}',
  meta_title       text    default '',
  meta_description text    default '',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

alter table public.blog_posts enable row level security;

create policy "Published posts are viewable by everyone"
  on public.blog_posts for select using (published = true);

create policy "Admins can view all posts"
  on public.blog_posts for select using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );

create policy "Admins can insert posts"
  on public.blog_posts for insert with check (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );

create policy "Admins can update posts"
  on public.blog_posts for update using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );

create policy "Admins can delete posts"
  on public.blog_posts for delete using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );


-- ============================================================
-- seo_pages
-- ============================================================

create table public.seo_pages (
  id            uuid    primary key default gen_random_uuid(),
  slug          text    unique not null,
  title         text    not null,
  description   text    not null default '',
  content       text    not null default '',
  h1            text    default '',
  canonical_url text    default '',
  og_image      text    default '',
  published     boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

alter table public.seo_pages enable row level security;

create policy "Published SEO pages are viewable by everyone"
  on public.seo_pages for select using (published = true);

create policy "Admins can manage SEO pages"
  on public.seo_pages for all using (
    exists (select 1 from public.profiles where id = auth.uid() and role = 'admin')
  );


-- ============================================================
-- Indexes
-- ============================================================

create index idx_profiles_phone    on public.profiles(phone);          -- fast phone OTP lookup
create index idx_bookings_user     on public.bookings(user_id);
create index idx_bookings_status   on public.bookings(status);
create index idx_bookings_phone    on public.bookings(phone);
create index idx_payments_user     on public.payments(user_id);
create index idx_payments_booking  on public.payments(booking_id);
create index idx_payments_ref      on public.payments(provider_ref);
create index idx_blog_slug         on public.blog_posts(slug);
create index idx_blog_published    on public.blog_posts(published);
create index idx_seo_slug          on public.seo_pages(slug);


-- ============================================================
-- updated_at trigger function
-- ============================================================

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger profiles_updated_at   before update on public.profiles   for each row execute function public.set_updated_at();
create trigger bookings_updated_at   before update on public.bookings   for each row execute function public.set_updated_at();
create trigger blog_posts_updated_at before update on public.blog_posts for each row execute function public.set_updated_at();
create trigger seo_pages_updated_at  before update on public.seo_pages  for each row execute function public.set_updated_at();


-- ============================================================
-- Migration: run these if you already have the table created
-- (safe to run on existing databases — add IF NOT EXISTS columns)
-- ============================================================

-- Bookings table
-- alter table public.bookings alter column user_id drop not null;
-- alter table public.bookings add column if not exists services  jsonb        not null default '[]';
-- alter table public.bookings add column if not exists building  text         not null default '';
-- alter table public.bookings add column if not exists name      text         not null default '';
-- alter table public.bookings add column if not exists phone     text         not null default '';

-- Payments table
-- alter table public.payments alter column user_id drop not null;

-- Profiles — make phone not null with default
-- alter table public.profiles alter column phone set not null;
-- alter table public.profiles alter column phone set default '';

-- Indexes
-- create index if not exists idx_profiles_phone   on public.profiles(phone);
-- create index if not exists idx_bookings_phone   on public.bookings(phone);
-- create index if not exists idx_payments_ref     on public.payments(provider_ref);

-- Drop old RLS policy that blocks server-side profile creation via service key
-- (service key bypasses RLS — no action needed, but if you added extra policies):
-- drop policy if exists "Public profiles are viewable by everyone" on public.profiles;
