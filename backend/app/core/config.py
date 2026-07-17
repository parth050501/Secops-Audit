from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    jwt_secret: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # Database URL is environment-driven:
    #   - Local dev (default): SQLite
    #   - Production: set DATABASE_URL to a Postgres async URL, e.g.
    #       postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME
    # Under docker-compose with the postgres service this is set automatically.
    database_url: str = "sqlite+aiosqlite:///./data/secops.db"

    environment: str = "qc"  # qc | production

    class Config:
        env_file = ".env"


settings = Settings()


def is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")
