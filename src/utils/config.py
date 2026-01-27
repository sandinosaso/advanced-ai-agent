"""
Configuration management for the application.
Loads settings from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import yaml
from loguru import logger

# Find project root (where .env file is located)
# This file is at src/utils/config.py, so project root is 2 levels up
_project_root = Path(__file__).parent.parent.parent

# Load environment variables from project root
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=True)
    logger.debug(f"Loaded .env from: {_env_file}")
else:
    logger.warning(f".env file not found at: {_env_file}")
    # Fallback to default behavior (current directory)
    load_dotenv(override=True)


@dataclass
class DatabaseConfig:
    """MySQL database configuration"""
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "root"))
    password: str = field(default_factory=lambda: os.getenv("DB_PWD", ""))
    database: str = field(default_factory=lambda: os.getenv("DB_NAME", "crewos"))
    encrypt_key: str = field(default_factory=lambda: os.getenv("DB_ENCRYPT_KEY", ""))
    
    def get_connection_string(self) -> str:
        """Build MySQL connection string for SQLAlchemy"""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            "?charset=utf8mb4"
        )


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # API Keys
    openai_api_key: str = Field(default="")
    
    # LLM Configuration
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.1)
    
    # Database Configuration (optional - not used by Settings, but won't error)
    db_host: str = Field(default="127.0.0.1")
    db_port: str = Field(default="3306")
    db_user: str = Field(default="root")
    db_pwd: str = Field(default="")
    db_name: str = Field(default="crewos")
    
    # SQL Agent Configuration
    sql_agent_max_iterations: int = Field(default=15)
    sql_sample_rows: int = Field(default=1)
    sql_max_tables_in_context: int = Field(default=20)
    sql_correction_max_attempts: int = Field(default=3)  # Max correction attempts
    sql_pre_validation_enabled: bool = Field(default=True)  # Enable pre-execution validation
    sql_confidence_threshold: float = Field(default=0.70)  # Minimum confidence for relationships (0.0-1.0)
    
    # SQL Agent Prompt Limits (to control token usage)
    sql_max_relationships_display: int = Field(default=50)  # Max relationships for initial display
    sql_max_relationships_in_prompt: int = Field(default=20)  # Max relationships in SQL generation/correction prompts
    sql_max_suggested_paths: int = Field(default=15)  # Max suggested join paths in join planning prompt
    sql_max_columns_in_schema: int = Field(default=50)  # Max columns shown in table schemas
    sql_max_columns_in_validation: int = Field(default=100)  # Max columns in validation error messages
    sql_max_columns_in_correction: int = Field(default=100)  # Max columns in correction agent schemas
    sql_max_sql_history_length: int = Field(default=100)  # Max SQL length in correction history
    sql_max_fallback_tables: int = Field(default=5)  # Max tables in fallback selection
    sql_max_tables_in_selection_prompt: int = Field(default=250)  # Max tables shown in table selection prompt
    
    # Orchestrator Agent Configuration
    orchestrator_temperature: float = Field(default=0.1)  # Temperature for orchestrator LLM (0.0-2.0)
    
    # Token Limits
    max_context_tokens: int = Field(default=120000)
    max_output_tokens: int = Field(default=4000)
    max_query_rows: int = Field(default=100)
    
    class Config:
        env_file = str(_project_root / ".env")
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env


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
        # Default to config/config.yaml in project root
        config_path = _project_root / "config" / "config.yaml"
    
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

# Log configuration status (but mask sensitive values)
if settings.openai_api_key:
    masked_key = settings.openai_api_key[:8] + "..." + settings.openai_api_key[-4:] if len(settings.openai_api_key) > 12 else "***"
    logger.info(f"✅ OpenAI API key loaded: {masked_key}")
else:
    logger.warning("⚠️  OPENAI_API_KEY not set in .env file - API calls will fail!")
