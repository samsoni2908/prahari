from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    PROJECT_NAME: str = "PRAHARI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "prahari"
    POSTGRES_USER: str = "prahari_app"
    POSTGRES_PASSWORD: str = "prahari_dev_password"

    DATABASE_URL: str = "postgresql+asyncpg://prahari_app:prahari_dev_password@localhost:5432/prahari"
    DATABASE_URL_SYNC: str = "postgresql://prahari_app:prahari_dev_password@localhost:5432/prahari"

    SECRET_KEY: str = "prahari-dev-secret-key-change-in-production-min32chars-sih26186"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LOGIN_ATTEMPTS_PER_WINDOW: int = 10
    LOGIN_WINDOW_SECONDS: int = 60

    AGGREGATION_FLOOR: int = 5
    SYNTHETIC_DATA_SEED: int = 26186

    WSI_WEIGHT_D: float = 0.25
    WSI_WEIGHT_R: float = 0.20
    WSI_WEIGHT_C: float = 0.15
    WSI_WEIGHT_N: float = 0.15
    WSI_WEIGHT_L: float = 0.10
    WSI_WEIGHT_H: float = 0.10
    WSI_WEIGHT_S: float = 0.05

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def require_deployment_secrets(self):
        if self.ENVIRONMENT.lower() in {"production", "demo"}:
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith("prahari-dev-"):
                raise ValueError("Deployment requires a non-default signing secret")
            for value in (self.DATABASE_URL, self.DATABASE_URL_SYNC):
                url = make_url(value)
                if url.get_backend_name() != "postgresql" or not url.password or url.password == "prahari_dev_password":
                    raise ValueError("Deployment requires configured PostgreSQL credentials")
            if self.DEBUG:
                raise ValueError("Deployment must disable DEBUG")
            if (not self.cors_origins or any(
                not origin.startswith("https://") or "*" in origin
                or "localhost" in origin or "127.0.0.1" in origin
                for origin in self.cors_origins
            )):
                raise ValueError("Deployment requires explicit HTTPS allowed origins")
        return self


settings = Settings()
