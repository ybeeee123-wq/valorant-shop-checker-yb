from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENCRYPTION_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./valshop.db"
    PUBLIC_SITE_URL: str = "http://localhost:5173"
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@example.com"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "VALSHOP <notifications@example.com>"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
