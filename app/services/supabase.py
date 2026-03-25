from supabase import create_client, Client

from app.config import settings

supabase_admin: Client = create_client(settings.supabase_url, settings.supabase_service_key)
supabase_public: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
