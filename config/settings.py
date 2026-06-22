from pydantic_settings import BaseSettings
from pydantic import BaseModel, ConfigDict  # se quiser ignorar extras

class Settings(BaseSettings):
    # model_config = ConfigDict(extra='ignore')  # (opcional) ignora envs extras

    # Opcionais: necessários apenas quando STORAGE_BACKEND="firebase".
    PROJECT_ID: str | None = None
    RTDB_URL: str | None = None
    API_PORT: int = 8000

    # SSQM — seleção do backend de armazenamento (porta/adaptador).
    # "firebase" (default, legado) ou "postgres".
    STORAGE_BACKEND: str = "firebase"
    DATABASE_URL: str | None = None

    OPENALEX_MAILTO: str | None = None  # <-- novo (opcional)

    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
