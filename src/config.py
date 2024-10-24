import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    OPENWEATHERMAP_API_KEY: str
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/weather_db"  # default to local
    CITIES: List[str] = ["Delhi", "Mumbai", "Chennai", "Bangalore", "Kolkata", "Hyderabad"]
    UPDATE_INTERVAL: int = 300  # 5 minutes in seconds
    TEMPERATURE_UNIT: str = "celsius"
    ALERT_TEMPERATURE_THRESHOLD: float = 35.0
    CONSECUTIVE_ALERTS_REQUIRED: int = 2
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True
    )

    @property
    def database_url(self) -> str:
        """Get the database URL based on the environment."""
        if self.ENVIRONMENT == "development":
            # Use localhost for local development
            return self.DATABASE_URL.replace("db:", "localhost:")
        return self.DATABASE_URL

settings = Settings()