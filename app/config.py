from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    jwt_secret: str = ""   # kept for compat; token verification now uses supabase_admin.auth.get_user
    frontend_url: str = "http://localhost:3000"
    ziina_merchant_id: str = "freezeAc"
    ziina_webhook_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
