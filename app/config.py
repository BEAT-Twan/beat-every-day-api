from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    DATABASE_URL: str
    SECRET_KEY: str
    ENV: str = "dev"

    STRAVA_CLIENT_ID: str
    STRAVA_CLIENT_SECRET: str
    STRAVA_VERIFY_TOKEN: str
    STRAVA_REDIRECT_URI: str

    CHALLENGE_TZ: str = "Europe/Amsterdam"
    PUBLISH_HOUR: int = 6
    GRACE_CUTOFF_HOUR: int = 12

    ADMIN_TOKEN: str = "beat-admin"

settings = Settings()
