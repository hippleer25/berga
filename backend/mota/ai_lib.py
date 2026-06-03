"""
ai_lib.py
─────────
Abstraction layer for LLM calls via LiteLLM.

Supports: OpenAI, Anthropic, Mistral, NVIDIA NIM, OpenRouter, etc.
"""

import os
os.environ.setdefault('LITELLM_LOG', 'WARNING')

import asyncio
import logging
import random
import time
import warnings
from typing import Generator, Literal, Optional

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import litellm
from litellm import completion, acompletion

logger = logging.getLogger(__name__)

# Automatically remove parameters not supported by the provider
litellm.drop_params = True

DEFAULT_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))

LLMUsage = Literal["cluster", "chatbot"]


# ------------------------------------------------------------------
# Configuração de modelos e credenciais
# ------------------------------------------------------------------

def _get_model_config(usage: LLMUsage) -> dict:
    prefix = usage.upper()

    model = os.getenv(f"{prefix}_LLM_MODEL")
    if not model:
        raise ValueError(
            f"[AI_LIB] {prefix}_LLM_MODEL não encontrada. "
            f"Exemplos: 'gpt-4', 'claude-3-sonnet-20240229', 'mistral/mistral-large-latest'"
        )

    api_key = os.getenv(f"{prefix}_LLM_API_KEY")
    api_base = os.getenv(f"{prefix}_LLM_API_BASE")

    if not api_key:
        raise ValueError(
            f"[AI_LIB] {prefix}_LLM_API_KEY não encontrada. "
            f"Defina a variável de ambiente {prefix}_LLM_API_KEY com uma chave de API válida."
        )

    config = {"model": model}
    config["api_key"] = api_key
    if api_base:
        config["api_base"] = api_base

    logger.info(
        f"[AI_LIB] Configuração {usage}: model={model}, "
        f"api_base={api_base or 'default'}, "
        f"api_key=***"
    )

    return config


# ------------------------------------------------------------------
# Text generation (non-streaming)
# ------------------------------------------------------------------

def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    usage: LLMUsage = "cluster",
    max_retries: int = 2,
) -> str | None:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(max_retries + 1):
        try:
            response = completion(
                model=config["model"],
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=config.get("api_key"),
                api_base=config.get("api_base"),
                timeout=DEFAULT_TIMEOUT,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None

        except litellm.RateLimitError as e:
            if attempt < max_retries:
                delay = min(2 ** (attempt + 1), 60) * (0.75 + random.random() * 0.5)
                logger.warning(
                    f"[AI_LIB] Rate-limited (429) on {config['model']} "
                    f"(attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {delay:.1f}s"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"[AI_LIB] Rate-limited after {max_retries + 1} attempts "
                    f"on {config['model']}"
                )
                return None
        except Exception as e:
            logger.error(f"[AI_LIB] Error calling LLM ({config['model']}): {e}")
            return None


# ------------------------------------------------------------------
# Streaming (legacy — compatibility)
# ------------------------------------------------------------------

def mota_text_stream(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    usage: LLMUsage = "chatbot",
) -> Generator[str, None, None]:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    try:
        response = completion(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            api_key=config.get("api_key"),
            api_base=config.get("api_base"),
            timeout=DEFAULT_TIMEOUT,
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except Exception as e:
        logger.error(f"[AI_LIB] Erro ao chamar LLM Stream ({config.get('model')}): {e}")
        raise


# ------------------------------------------------------------------
# Tool calling (function calling)
# ------------------------------------------------------------------

def call_llm_with_tools(
    prompt: str,
    tools: list[dict],
    system_prompt: str | None = None,
    tool_choice: str | dict | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    usage: LLMUsage = "chatbot",
):
    """
    Chamada não-streaming com definições de ferramentas (function calling).

    Args:
        prompt:          Prompt / mensagem do usuário
        tools:           Lista de definições de ferramentas no formato OpenAI
        system_prompt:   Prompt do sistema (instruções para o modelo)
        tool_choice:     Controla se/qual ferramenta o modelo deve chamar.
                         Opções: "auto", "required", "none",
                         ou {"type": "function", "function": {"name": "..."}}
        model:           Modelo específico (sobrescreve config padrão)
        max_tokens:      Máximo de tokens na resposta
        temperature:     Temperatura
        usage:           Tipo de uso ('cluster' ou 'chatbot')
    """
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": config["model"],
        "messages": messages,
        "tools": tools,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "api_key": config.get("api_key"),
        "api_base": config.get("api_base"),
        "timeout": DEFAULT_TIMEOUT,
    }

    # Only add tool_choice if the caller explicitly requested it.
    # litellm.drop_params=True removes the parameter if the provider doesn't support it.
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice

    try:
        response = completion(**kwargs)
        return response

    except Exception as e:
        logger.error(f"[AI_LIB] Error calling LLM with tools ({config.get('model')}): {e}")
        return None


# ------------------------------------------------------------------
# Streaming with message history
# ------------------------------------------------------------------

def stream_llm_response(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
    usage: LLMUsage = "chatbot",
) -> Generator[str, None, None]:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    try:
        response = completion(
            model=config["model"],
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            api_key=config.get("api_key"),
            api_base=config.get("api_base"),
            timeout=DEFAULT_TIMEOUT,
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except Exception as e:
        logger.error(f"[AI_LIB] Error streaming LLM ({config.get('model')}): {e}")
        raise


# ------------------------------------------------------------------
# Async versions
# ------------------------------------------------------------------

async def agenerate_text(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    usage: LLMUsage = "cluster",
    max_retries: int = 2,
) -> str | None:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(max_retries + 1):
        try:
            response = await acompletion(
                model=config["model"],
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=config.get("api_key"),
                api_base=config.get("api_base"),
                timeout=DEFAULT_TIMEOUT,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None

        except litellm.RateLimitError as e:
            if attempt < max_retries:
                delay = min(2 ** (attempt + 1), 60) * (0.75 + random.random() * 0.5)
                logger.warning(
                    f"[AI_LIB] Rate-limited (429) on {config['model']} "
                    f"(attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"[AI_LIB] Rate-limited after {max_retries + 1} attempts "
                    f"on {config['model']}"
                )
                return None
        except Exception as e:
            logger.error(f"[AI_LIB] Error calling LLM async ({config['model']}): {e}")
            return None


# ------------------------------------------------------------------
# Utilitários
# ------------------------------------------------------------------

def list_supported_models() -> dict[str, list[str]]:
    return {
        "openai": [
            "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022", "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
        ],
        "mistral": [
            "mistral/mistral-large-latest", "mistral/mistral-medium-latest",
            "mistral/mistral-small-latest", "mistral/open-mistral-7b",
        ],
        "openrouter": [
            "openrouter/anthropic/claude-3-opus",
            "openrouter/meta-llama/llama-3.1-70b-instruct",
            "openrouter/google/gemini-pro-1.5",
        ],
        "nvidia_nim": [
            "nvidia_nim/meta/llama-3.1-8b-instruct",
            "nvidia_nim/meta/llama-3.1-70b-instruct",
            "nvidia_nim/mistralai/mixtral-8x7b-instruct-v0.1",
        ],
    }


def get_provider_from_model(model: str) -> str:
    model_lower = model.lower()
    if "/" in model:
        return model.split("/")[0]
    if model_lower.startswith("gpt"):
        return "openai"
    elif model_lower.startswith("claude"):
        return "anthropic"
    elif "mistral" in model_lower or "mixtral" in model_lower:
        return "mistral"
    return "unknown"