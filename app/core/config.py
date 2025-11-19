from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "FastAPI App"

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    SLACK_CLIENT_ID: str
    SLACK_CLIENT_SECRET: str
    SLACK_REDIRECT_URI: str

    model_config = ConfigDict(env_file=".env")

settings = Settings()