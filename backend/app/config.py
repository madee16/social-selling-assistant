from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_db_url: str
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    frontend_url: str = "http://localhost:5173"
    database_echo: bool = False

    gemini_api_key: str | None = None
    nvidia_api_key: str | None = None
    supabase_url: str = ""
    supabase_anon_key: str = ""
    # Service-role key (server-side only, never shipped to the browser). Used
    # for privileged Supabase Storage writes so the bucket can stay private.
    supabase_service_key: str = ""

    n8n_webhook_url: str = ""
    n8n_api_key: str = ""

    # Default LLM model for chat responses/extraction. Override in each env.
    nvidia_model: str = "nvidia/nemotron-3-super-120b-a12b"

    # Runtime environment label (development/staging/production). Used only for
    # logs and clarity; it does NOT itself enable/disable anything.
    app_env: str = "development"

    # --- WhatsApp / Meta Business Platform integration -------------------------
    # Master switch. Defaults to DISABLED so production (main) never processes
    # real WhatsApp traffic unless explicitly enabled via the environment.
    # Only the development/staging environment (develop branch) sets this true.
    whatsapp_enabled: bool = False
    # Human-readable label of the WhatsApp config environment (e.g. "development")
    # shown in startup logs so it is immediately obvious which credentials are in play.
    whatsapp_env: str = ""
    # Webhook verification token. Must match the token configured in the Meta
    # Developer dashboard. Falls back to the legacy default for backwards
    # compatibility with the existing Meta setup; override in each environment.
    whatsapp_verify_token: str = "social-selling-verify-2026"
    messenger_verify_token: str = "social-selling-verify-2026"
    # Graph API base URL for all Meta WhatsApp calls.
    whatsapp_graph_api_base: str = "https://graph.facebook.com/v21.0"
    # Environment-level credentials. Intended for the development/staging env
    # only. When set they take priority over the per-tenant values stored in
    # widget_settings. Keep these OUT of any production environment.
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    # Meta App Secret used to verify the X-Hub-Signature-256 HMAC on webhook
    # POSTs. REQUIRED in production (webhook POSTs are rejected without a
    # valid signature). Empty = skip verification with a warning (dev only).
    whatsapp_app_secret: str = ""

    # Key used to encrypt integration tokens (WhatsApp/Messenger) at rest
    # in widget_settings. Any secret string works (it is hashed into a Fernet
    # key). If empty, a key is derived from secret_key so tokens are never
    # stored in plaintext. Override in production and keep it stable.
    token_encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
