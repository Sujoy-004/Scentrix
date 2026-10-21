"""Settings parsing tests (env-var driven configuration)."""

from app.config import Settings


def test_allowed_origins_accepts_comma_separated_env(monkeypatch):
    """ALLOWED_ORIGINS as a comma-separated string must not raise SettingsError."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example.com, https://b.example.com")
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == ["https://a.example.com", "https://b.example.com"]


def test_allowed_origins_accepts_single_origin(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://only.example.com")
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == ["https://only.example.com"]


def test_allowed_origins_accepts_json_array(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://a.example.com","https://b.example.com"]')
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == ["https://a.example.com", "https://b.example.com"]


def test_allowed_origins_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    settings = Settings(_env_file=None)
    assert "http://localhost:3000" in settings.allowed_origins


def test_database_url_reads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/scentrix-test.db")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:////tmp/scentrix-test.db"


def test_bare_postgres_url_is_pinned_to_psycopg2(monkeypatch):
    """SQLAlchemy 2.1 defaults a bare postgresql:// URL to psycopg3.

    The app ships psycopg2, so a managed provider's URL must be rewritten or
    the app dies at import time with "No module named 'psycopg'".
    """
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pw@ep-abc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require",
    )
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg2://")
    assert "-pooler" in settings.database_url
    assert "sslmode=require" in settings.database_url


def test_explicit_driver_in_the_url_is_left_alone(monkeypatch):
    for url in (
        "postgresql+psycopg://user:pw@host/db",
        "postgresql+asyncpg://user:pw@host/db",
        "sqlite:///./local.db",
    ):
        monkeypatch.setenv("DATABASE_URL", url)
        assert Settings(_env_file=None).database_url == url
