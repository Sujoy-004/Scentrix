"""Backend configuration module."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str

    # Neo4j
    neo4j_uri: str = Field(
        default="neo4j://localhost:7687",
        validation_alias=AliasChoices("NEO4J_URI", "NEO4J_URL"),
    )
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("NEO4J_USERNAME", "NEO4J_USER"),
    )
    neo4j_password: str = Field(
        default="neo4j_password",
        validation_alias=AliasChoices("NEO4J_PASSWORD", "NEO4J_PW"),
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "CELERY_BROKER_URL"),
    )

    # Supabase
    supabase_url: str | None = None
    supabase_anon_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_ANON_KEY"),
    )
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY"),
    )
    supabase_jwt_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_JWT_SECRET"),
    )

    # JWT
    jwt_secret_key: str = Field(
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    access_token_expire_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES"),
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRE_DAYS"),
    )
    data_encryption_key: str = Field(
        validation_alias=AliasChoices("DATA_ENCRYPTION_KEY"),
    )

    # Sentry & Logging
    sentry_dsn: str | None = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 1.0
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_prefix: str = "/api/v1"

    # CORS
    allowed_origins: list[str] = [
        "https://scentrix-one.vercel.app",
    ]

    # Pinecone Vector Search
    pinecone_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("PINECONE_API_KEY")
    )
    pinecone_environment: str = Field(
        default="us-west4-gcp", validation_alias=AliasChoices("PINECONE_ENVIRONMENT")
    )
    pinecone_index_name: str = Field(
        default="Scentrix-fragrances", validation_alias=AliasChoices("PINECONE_INDEX_NAME")
    )
    pinecone_graph_index_name: str = Field(
        default="Scentrix-graph", validation_alias=AliasChoices("PINECONE_GRAPH_INDEX_NAME")
    )

    # Google (Gemini) - For Digital Sommelier
    google_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("GOOGLE_API_KEY")
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Ensure SQLAlchemy async engine receives an async driver URL."""
        if not isinstance(value, str):
            return value

        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql+psycopg2://"):
            return value.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


settings = Settings()
