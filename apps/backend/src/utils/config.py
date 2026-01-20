"""
Configuration management for the application.
Loads settings from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import yaml

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # API Keys
    openai_api_key: str = Field(default="")
    
    # LLM Configuration
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.1)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class VectorDBConfig(BaseModel):
    """Vector database configuration for RAG."""
    collection_name: str = "knowledge_base"
    similarity_threshold: float = 0.7
    max_results: int = 10
    embedding_model: str = "text-embedding-3-small"


class LLMConfig(BaseModel):
    """LLM configuration."""
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 2000


class AppSettings(BaseModel):
    """Application settings."""
    name: str = "AI Learning Project"
    environment: str = "development"
    log_level: str = "INFO"


class AppConfig(BaseModel):
    """Complete application configuration."""
    llm: LLMConfig
    vector_db: VectorDBConfig
    app: AppSettings


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Load application configuration from YAML file.
    
    Args:
        config_path: Path to config file (optional, defaults to config/config.yaml)
        
    Returns:
        AppConfig object with loaded configuration
    """
    if config_path is None:
        # Default to config/config.yaml in backend directory
        backend_dir = Path(__file__).parent.parent.parent
        config_path = backend_dir / "config" / "config.yaml"
    
    if not config_path.exists():
        # Return default configuration
        return AppConfig(
            llm=LLMConfig(),
            vector_db=VectorDBConfig(),
            app=AppSettings()
        )
    
    # Load YAML configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # Parse into Pydantic models
    return AppConfig(**config_data)


# Create global settings instance
settings = Settings()
