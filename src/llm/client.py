"""
LLM client factory

Creates appropriate LLM instances based on provider configuration.
"""

from typing import Optional
from loguru import logger

from src.config.settings import settings


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
