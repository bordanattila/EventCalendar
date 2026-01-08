"""
Configuration management for the Calendar Agent service.

Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./calendar.db",
        description="Database connection URL"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Agent Configuration
    llm_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    llm_temperature: float = Field(default=0.1, description="LLM temperature")
    max_tool_iterations: int = Field(default=10, description="Max tool call iterations")
    
    # Timezone Configuration
    default_timezone: str = Field(
        default="America/New_York",
        description="Default timezone for event parsing"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()

