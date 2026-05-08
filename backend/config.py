"""
AgriNet AI — Configuration & Settings
All environment variables loaded via pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_secret: str = "changeme_in_production_please"
    environment: str = "development"
    cors_origins: str = "*"

    # OpenWeatherMap
    openweathermap_key: str = ""

    # OpenCage geocoding
    opencage_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # OpenRouter LLM
    openrouter_api_key: str = ""
    openrouter_model: str = "mistralai/mistral-7b-instruct:free"

    # LibreTranslate
    libre_translate_url: str = "https://libretranslate.com"
    libre_translate_key: str = ""

    # Derived
    @property
    def has_weather_api(self) -> bool:
        return bool(self.openweathermap_key and self.openweathermap_key != "your_openweathermap_api_key_here")

    @property
    def has_geocode_api(self) -> bool:
        return bool(self.opencage_key and self.opencage_key != "your_opencage_api_key_here")

    @property
    def has_supabase(self) -> bool:
        return bool(
            self.supabase_url 
            and "supabase.co" in self.supabase_url 
            and "your-project-id" not in self.supabase_url
        )

    @property
    def has_llm(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_api_key != "sk-or-v1-your-key-here")

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
