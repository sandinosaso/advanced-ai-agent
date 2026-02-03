"""
Configuration management for the application.
Loads settings from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
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
    
    # LLM Provider Selection
    llm_provider: str = Field(default="openai")  # Options: "openai" | "ollama"
    
    # API Keys
    openai_api_key: str = Field(default="")
    
    # OpenAI Configuration
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.1)
    
    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3")
    ollama_embedding_model: str = Field(default="all-MiniLM-L6-v2")  # sentence-transformers model
    
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
    
    # Agent Enable/Disable Flags (for testing and offline operation)
    enable_sql_agent: bool = Field(default=True)  # Enable SQL agent for database queries
    enable_rag_agent: bool = Field(default=True)  # Enable RAG agent for document retrieval
    
    # Domain Ontology Configuration
    domain_registry_enabled: bool = Field(default=True)  # Enable domain ontology layer
    domain_registry_path: str = Field(default="artifacts/domain_registry.json")  # Path to domain vocabulary registry
    domain_extraction_enabled: bool = Field(default=True)  # Enable LLM-based domain term extraction
    domain_fallback_to_text_search: bool = Field(default=True)  # Fallback to text search when no domain match
    
    # Token Limits
    max_context_tokens: int = Field(default=120000)
    max_output_tokens: int = Field(default=4000)
    max_query_rows: int = Field(default=100)
    
    # Conversation Memory Configuration
    conversation_db_path: str = Field(default="data/conversations.db")
    conversation_max_age_hours: int = Field(default=24)
    conversation_cleanup_interval_hours: int = Field(default=1)
    max_conversation_messages: int = Field(default=20)
    conversation_memory_strategy: str = Field(default="simple")  # "simple" | "tiered" (for future)
    conversation_db_retry_attempts: int = Field(default=3)
    conversation_db_retry_delay: float = Field(default=0.1)
    
    # Follow-up Question Memory Configuration
    query_result_memory_size: int = Field(default=3)  # Keep last N query results for follow-ups
    followup_detection_enabled: bool = Field(default=True)  # Enable follow-up question detection
    followup_max_context_tokens: int = Field(default=2000)  # Max tokens for previous results context
    
    class Config:
        env_file = str(_project_root / ".env")
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env


# Create global settings instance
settings = Settings()

# Resolve conversation DB path to absolute
_conversation_db_path = Path(settings.conversation_db_path)
if not _conversation_db_path.is_absolute():
    _conversation_db_path = _project_root / _conversation_db_path

# Store resolved path as attribute (for use in conversation_db.py)
settings.conversation_db_path_resolved = str(_conversation_db_path)


def _validate_ollama_model():
    """Validate that the configured Ollama model is available on the server."""
    import httpx
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        response.raise_for_status()
        models_data = response.json()
        available_models = [model.get("name", "").split(":")[0] for model in models_data.get("models", [])]
        
        # Check if the configured model is available (handle both "llama3" and "llama3:latest")
        model_name = settings.ollama_model.split(":")[0]
        if model_name not in available_models:
            logger.error(
                f"❌ Ollama model '{settings.ollama_model}' is not available on the server.\n"
                f"   Available models: {', '.join(available_models) if available_models else 'None'}\n"
                f"   To install the model, run: ollama pull {settings.ollama_model}"
            )
        else:
            logger.debug(f"✅ Ollama model '{settings.ollama_model}' is available")
    except httpx.RequestError as e:
        logger.warning(
            f"⚠️  Could not connect to Ollama server at {settings.ollama_base_url} to validate model. "
            f"Make sure Ollama is running. Error: {e}"
        )
    except Exception as e:
        logger.warning(f"⚠️  Could not validate Ollama model availability: {e}")


# Log configuration status and validate Ollama model if needed
if settings.llm_provider == "openai":
    if settings.openai_api_key:
        masked_key = settings.openai_api_key[:8] + "..." + settings.openai_api_key[-4:] if len(settings.openai_api_key) > 12 else "***"
        logger.info(f"✅ LLM Provider: OpenAI | Model: {settings.openai_model} | API key loaded: {masked_key}")
    else:
        logger.warning("⚠️  LLM Provider: OpenAI but OPENAI_API_KEY not set in .env file - API calls will fail!")
elif settings.llm_provider == "ollama":
    logger.info(f"✅ LLM Provider: Ollama | Base URL: {settings.ollama_base_url} | Model: {settings.ollama_model}")
    # Validate Ollama model availability at startup
    _validate_ollama_model()
else:
    logger.warning(f"⚠️  Unknown LLM provider: {settings.llm_provider}. Supported: 'openai', 'ollama'")


def create_llm(temperature: Optional[float] = None, max_completion_tokens: Optional[int] = None, model: Optional[str] = None):
    """
    Factory function to create appropriate LLM based on provider configuration.
    
    Args:
        temperature: Generation temperature (defaults to provider-specific default)
        max_completion_tokens: Max tokens for completion (defaults to settings.max_output_tokens)
        model: Model name (defaults to provider-specific model)
    
    Returns:
        LangChain ChatModel instance (ChatOpenAI or ChatOllama)
    """
    provider = settings.llm_provider.lower()
    max_tokens = max_completion_tokens or settings.max_output_tokens
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        
        return ChatOpenAI(
            model=model or settings.openai_model,
            temperature=temperature if temperature is not None else settings.openai_temperature,
            max_completion_tokens=max_tokens,
        )
    
    elif provider == "ollama":
        # Use langchain-community's ChatOllama (compatible with langchain-core 1.2.7)
        try:
            from langchain_community.chat_models import ChatOllama
        except ImportError:
            raise ImportError(
                "Ollama support requires 'langchain-community'. "
                "Install it with: pip install langchain-community"
            )
        
        # Validate Ollama server is accessible and model is available
        import httpx
        model_to_use = model or settings.ollama_model
        try:
            response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
            response.raise_for_status()
            models_data = response.json()
            available_models = [m.get("name", "").split(":")[0] for m in models_data.get("models", [])]
            
            # Check if the model is available
            model_name = model_to_use.split(":")[0]
            if model_name not in available_models:
                error_msg = (
                    f"Ollama model '{model_to_use}' is not available on the server. "
                    f"Available models: {', '.join(available_models) if available_models else 'None'}. "
                    f"To install: ollama pull {model_to_use}"
                )
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
        except httpx.RequestError as e:
            error_msg = (
                f"Could not connect to Ollama server at {settings.ollama_base_url}. "
                f"Make sure Ollama is running. Error: {e}"
            )
            logger.error(f"❌ {error_msg}")
            raise ConnectionError(error_msg) from e
        except ValueError:
            # Re-raise ValueError from model check
            raise
        except Exception as e:
            logger.warning(
                f"⚠️  Could not validate Ollama model availability: {e}. "
                f"Proceeding anyway, but model may not be available."
            )
        
        return ChatOllama(
            model=model_to_use,
            base_url=settings.ollama_base_url,
            temperature=temperature if temperature is not None else settings.openai_temperature,
            num_predict=max_tokens,  # Ollama uses num_predict instead of max_completion_tokens
        )
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported: 'openai', 'ollama'")
