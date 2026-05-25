from pydantic_settings import BaseSettings
from pydantic import BaseModel, ConfigDict  # se quiser ignorar extras

class Settings(BaseSettings):
    # model_config = ConfigDict(extra='ignore')  # (opcional) ignora envs extras

    PROJECT_ID: str
    RTDB_URL: str
    API_PORT: int = 8000

    OPENALEX_MAILTO: str | None = None  # <-- novo (opcional)

    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
