from pydantic_settings import BaseSettings

_DEFAULT_DB_PASSWORD = "mediainfo_dev"


class Settings(BaseSettings):
    DATABASE_URL: str = f"postgresql+asyncpg://mediainfodb:{_DEFAULT_DB_PASSWORD}@localhost:5432/mediainfodb"
    ALLOWED_BROWSE_ROOTS: str = "/media"
    SCAN_INTERVAL_MINUTES: int = 360

    @property
    def allowed_roots_list(self) -> list[str]:
        return [r.strip() for r in self.ALLOWED_BROWSE_ROOTS.split(",") if r.strip()]

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")


settings = Settings()
