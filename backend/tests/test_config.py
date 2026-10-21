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
