from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RoofMap AI"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/roofmap_ai"
    cors_origins: str = "*"  # comma-separated for production, e.g. https://roofmap.vercel.app

    # Optional: swap vision backend later
    vision_backend: str = "stub"  # stub | yolo (yolo not wired yet)

    @property
    def database_url_sync(self) -> str:
        """Normalize Supabase `postgresql://` to SQLAlchemy psycopg3 driver."""
        u = self.database_url.strip()
        if "+psycopg" in u:
            return u
        if u.startswith("postgresql://"):
            return "postgresql+psycopg://" + u[len("postgresql://") :]
        if u.startswith("postgres://"):
            return "postgresql+psycopg://" + u[len("postgres://") :]
        return u

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
