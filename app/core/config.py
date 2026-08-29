# app/core/config.py
"""
Application Configuration
=========================
This module uses pydantic-settings to load configuration from environment
variables (and optionally a .env file).

WHY pydantic-settings?
----------------------
You already understand that hardcoding config (DB passwords, API keys) is bad.
pydantic-settings gives you three things Go engineers typically build manually:

1. Type safety  — every setting is typed; a string "true" becomes bool True
2. Validation   — the app crashes at startup with a clear message if a required
                  variable is missing, instead of failing silently mid-request
3. .env support — the Settings class automatically reads from a .env file in
                  development, and from real env vars in production (Docker,
                  Kubernetes secrets, etc.)

HOW it works underneath:
------------------------
BaseSettings inherits from Pydantic's BaseModel. When you instantiate Settings(),
pydantic-settings:
  1. Looks at each field name (e.g., APP_NAME)
  2. Searches os.environ for that name (case-insensitive)
  3. If not found, tries the .env file specified in model_config
  4. Falls back to the default value if provided
  5. Validates the type and raises ValidationError if invalid

12-Factor App principle:
------------------------
This follows https://12factor.net/config — configuration comes from the
environment, not from config files committed to version control.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings.

    Fields with defaults are optional.
    Fields without defaults are required — the app won't start without them.
    """

    model_config = SettingsConfigDict(
        # Which .env file to load in development
        env_file=".env",
        # If the .env file doesn't exist, don't error — just use real env vars
        env_file_encoding="utf-8",
        # Ignore extra variables in the environment that we don't declare here
        extra="ignore",
        # Case-insensitive matching: APP_NAME and app_name both work
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # Application metadata
    # -------------------------------------------------------------------------
    app_name: str = Field(default="AI Document Intelligence", description="Human-readable application name")
    app_version: str = Field(default="0.1.0", description="Application version (semver)")
    environment: str = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=False, description="Enable debug mode (more verbose output)")
    log_level: str = Field(default="INFO", description="Python logging level")

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    api_v1_prefix: str = Field(default="/api/v1", description="URL prefix for all v1 routes")

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    # Stored as a comma-separated string in the env var because environment
    # variables are always strings. We parse it into a list below.
    allowed_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="ALLOWED_ORIGINS",
        description="Comma-separated list of allowed CORS origins",
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Parse the comma-separated origins string into a list."""
        return [o.strip() for o in self.allowed_origins_str.split(",") if o.strip()]

    # -------------------------------------------------------------------------
    # Document storage (Phase 2)
    # -------------------------------------------------------------------------
    upload_dir: str = Field(default="data/documents", description="Directory for uploaded files")
    max_upload_size_mb: int = Field(default=50, description="Maximum upload file size in megabytes")

    # -------------------------------------------------------------------------
    # Database (Phase 2)
    # -------------------------------------------------------------------------
    # WHY Optional with None default?
    # Phase 1 tests run without a real database. Making this Optional means
    # the app can still start/test without DATABASE_URL set.
    # Phase 2 onwards: the app will require this at runtime (checked in db/database.py).
    database_url: str | None = Field(
        default=None,
        description="Async SQLAlchemy database URL. "
        "Format: postgresql+asyncpg://user:password@host:port/dbname",
    )


# -----------------------------------------------------------------------------
# Singleton pattern using lru_cache
# -----------------------------------------------------------------------------
# WHY lru_cache?
# Reading and validating environment variables has a cost. We only want to do it
# once per process lifetime, not once per request.
#
# get_settings() is a dependency function — FastAPI will call it for every
# request that declares it as a dependency. lru_cache ensures the Settings
# object is constructed exactly once and reused.
#
# In tests, you can override this with app.dependency_overrides[get_settings]
# to inject test-specific configuration without touching real env vars.
# -----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
