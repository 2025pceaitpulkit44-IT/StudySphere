from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://studysphere:studysphere@localhost:5432/studysphere"
    jwt_secret: str
    jwt_expire_minutes: int = 120
    admin_invite_code: str = ""
    allowed_email_domains: str = ""
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "../uploads"
    max_upload_mb: int = 25

    seed_admin_password: str = "Admin@12345"
    seed_student_password: str = "Student@12345"

    llm_provider: str = "gemini"          # gemini | openai | anthropic | ollama
    llm_model: str = ""                   # empty -> sensible default per provider
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"   # also works for Groq and other OpenAI-compatible APIs
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.30     # cosine similarity below this = "not in the knowledge base"
    embedding_provider: str = "local"      # local | hashing (offline, lower quality; used in tests)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def email_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
