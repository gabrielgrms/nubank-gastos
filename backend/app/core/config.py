from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/nubank_gastos"
    jwt_secret_key: str = "e7f4b7084d56455aa7813bc4da8bfc3806f4868f07724d9ea0e80b737bd60589"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000,http://frontend"

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_sender: str = "no-reply@nubank-gastos.local"
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
