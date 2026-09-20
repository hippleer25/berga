"""
ai_lib.py
─────────
Abstraction layer for LLM calls via LiteLLM.

Supports: OpenAI, Anthropic, Mistral, NVIDIA NIM, OpenRouter, etc.

Gateways exposing multiple protocol families under a single base URL
(e.g. opencode go: chat/completions, /responses, /v1/messages) are routed
through `mota.model_routing`, with a runtime ladder that retries the next
protocol family when the gateway answers with a generic 500.
"""

import os
os.environ.setdefault('LITELLM_LOG', 'WARNING')

import asyncio
import hashlib
import logging
import random
import time
import warnings
from typing import Generator, Literal, Optional

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

_litellm_module = None


class _LiteLLMProxy:
    """
    Lazy litellm loader. Importing litellm costs ~130 MB RSS and would
    otherwise happen at API boot via the chat import chain — even in
    sessions that never touch AI. The actual import is deferred to the
    first attribute/call access.
    """

    def __getattr__(self, name):
        global _litellm_module
        if _litellm_module is None:
            import litellm as _mod  # deferred heavy import
            _mod.drop_params = True
            _litellm_module = _mod
        return getattr(_litellm_module, name)


litellm = _LiteLLMProxy()


def completion(*args, **kwargs):
    return litellm.completion(*args, **kwargs)


def acompletion(*args, **kwargs):
    return litellm.acompletion(*args, **kwargs)

from mota import model_routing

logger = logging.getLogger(__name__)

# Automatically remove parameters not supported by the provider
# litellm.drop_params=True is set on first lazy import in _LiteLLMProxy.

DEFAULT_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))

LLMUsage = Literal["cluster", "chatbot", "routing", "summarize", "synthesis"]

# Fallback chain for optional tiers. If a tier's own env vars are not set,
# we fall back to the next tier in the chain. "cluster" and "chatbot" are
# the base tiers and remain required (no fallback).
_TIER_FALLBACK: dict[str, str | None] = {
    "cluster": None,
    "chatbot": None,
    "routing": "chatbot",
    "summarize": "chatbot",
    "synthesis": "chatbot",
}

# Remembers which models already got their streaming-style warning.
_stream_style_warned: set[str] = set()


# ------------------------------------------------------------------
# Configuração de modelos e credenciais
# ------------------------------------------------------------------

def _session_headers(config: dict, session_id: str | None = None) -> dict:
    """
    Provider-specific headers. opencode zen (Console Go) refuses requests
    without `x-opencode-session`; we send a stable per-conversation id when
    the caller provides one (chat flows) or a fresh random id otherwise
    (stateless background calls — provider context lives in our messages).
    """
    api_base = (config.get("api_base") or "").lower()
    if "opencode" in api_base:
        if not session_id:
            session_id = hashlib.sha256(os.urandom(32)).hexdigest()
        return {"x-opencode-session": f"berga-{session_id}"}
    return {}


def _get_model_config(usage: LLMUsage) -> dict:
    fallback = _TIER_FALLBACK.get(usage)
    fb_prefix = fallback.upper() if fallback else None

    def _creds_for(prefix: str) -> tuple[str | None, str | None, str | None]:
        model = os.getenv(f"{prefix}_LLM_MODEL")
        if not model:
            return None, None, None
        return model, os.getenv(f"{prefix}_LLM_API_KEY"), os.getenv(f"{prefix}_LLM_API_BASE")

    # Try the requested tier first; if its credentials are incomplete or
    # invalid, fall back to the next tier instead of crashing the caller.
    for prefix in [usage.upper(), fb_prefix] if fb_prefix else [usage.upper()]:
        model, api_key, api_base = _creds_for(prefix)
        if model and api_key:
            effective_usage = prefix.lower()
            break
    else:
        raise ValueError(
            f"[AI_LIB] Nenhuma credencial completa encontrada para o tier '{usage}'"
            + (f" nem para o fallback '{fallback}'" if fallback else "")
            + ". Verifique *_LLM_MODEL e *_LLM_API_KEY."
        )

    if effective_usage != usage:
        logger.warning(
            f"[AI_LIB] Tier '{usage}' sem credenciais completas — "
            f"usando fallback '{effective_usage}'"
        )

    config = {"model": model}
    config["api_key"] = api_key
    if api_base:
        config["api_base"] = api_base

    logger.info(
        f"[AI_LIB] Configuração {usage} → model={model}, "
        f"api_base={api_base or 'default'}, "
        f"api_key=***"
        + (f" (fallback: {effective_usage})" if effective_usage != usage else "")
    )

    return config


# ------------------------------------------------------------------
# Protocol routing helpers (multi-surface gateways)
# ------------------------------------------------------------------

def _resolve_route(config: dict, session_id: str | None):
    """
    Resolve where the request should actually go.

    Returns (route, headers) where route is None for plain single-protocol
    providers, or a dict with the litellm model string / api_base / protocol
    for multi-surface gateways. Routeinfo is used by the fallback ladder in
    ai_lib and by call sites that need protocol-conditional parameters
    (e.g. stream_options).
    """
    if not model_routing.is_opencode(config.get("api_base")):
        return None, _session_headers(config, session_id)

    bare = model_routing.bare_model_name(config["model"])
    protocol = model_routing.resolve(bare, config.get("api_base"))
    model_str, api_base = model_routing.litellm_target(
        bare, protocol, config.get("api_base")
    )
    route = {
        "bare": bare,
        "protocol": protocol,
        "model": model_str,
        "api_base": api_base,
        "base_api_url": config.get("api_base"),
        "min_output": model_routing.min_output_tokens(
            bare, config.get("api_base")
        ),
    }
    headers = _session_headers(config, session_id)
    logger.debug(f"[AI_LIB] Route {bare} → protocol={protocol}, model={model_str}")
    return route, headers


def _target_for(route: dict, protocol: str) -> dict:
    """Route dict with a different protocol family (fallback ladder step)."""
    model_str, api_base = model_routing.litellm_target(
        route["bare"], protocol, route["base_api_url"]
    )
    return {**route, "protocol": protocol, "model": model_str, "api_base": api_base}


def _floor_max_tokens(route: dict | None, max_tokens: int) -> int:
    """Clamp max_tokens up to the model's minimum output budget.

    Reasoning models on the gateway reject requests whose output budget is
    below the provider's minimum (reasoning consumes part of it), which
    surfaces as a deceptive "unable to complete request: max_output_tokens"
    on EVERY protocol surface. Raising the budget avoids that whole class
    of failure at a small extra cost for short calls (router/self-check).
    """
    if route is None:
        return max_tokens
    return max(max_tokens, int(route.get("min_output") or 0))


def _protocol_sequence(route: dict) -> list[str]:
    if route is None:
        return [None]
    seq = model_routing.protocol_sequence(route["bare"], route["base_api_url"])
    return seq  # best-known first, then the rest of the ladder


def _on_protocol_success(route: dict) -> None:
    if route is not None:
        model_routing.record(route["bare"], route["base_api_url"], route["protocol"])


def _is_ladder_error(e: Exception) -> bool:
    """Generic errors worth retrying under another protocol family.

    The gateway's wrong-surface failure is a 500 ("Internal server error")
    which litellm surfaces as InternalServerError/APIConnectionError.
    Rate limits/auth errors are NOT protocol problems — re-raise as-is.
    """
def _is_ladder_error(e: Exception, include_timeout: bool = False) -> bool:
    """Generic errors worth retrying under another protocol family.

    The gateway's wrong-surface failure is a 500 ("Internal server error")
    which litellm surfaces as InternalServerError/APIConnectionError.
    Rate limits/auth errors are NOT protocol problems — re-raise as-is.
    Timeouts only count inside the pseudo-stream fallback (a hanging
    surface should push us to the next protocol there), never in the
    normal retry loops — otherwise every transient hiccup would be paid
    with up to three full timeouts.
    """
    if isinstance(e, (litellm.RateLimitError, litellm.AuthenticationError)):
        return False
    if include_timeout and isinstance(e, litellm.Timeout):
        return True
    if isinstance(
        e, (litellm.InternalServerError, litellm.APIConnectionError, litellm.BadRequestError, litellm.APIError)
    ):
        return True
    return False


def _log_protocol_retry(e: Exception, model: str, next_protocol: str) -> None:
    logger.warning(
        f"[AI_LIB] Request failed on {model} ({type(e).__name__}: {e}) — "
        f"retrying through protocol '{next_protocol}'"
    )


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
    usage_out: dict | None = None,
    session_id: str | None = None,
) -> str | None:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    route, headers = _resolve_route(config, session_id)
    max_tokens = _floor_max_tokens(route, max_tokens)

    ladder_error = None
    tokens_budget = max_tokens

    for attempt in range(max_retries + 1):
        protocol_error = False
        try:
            response = completion(
                model=route["model"] if route else config["model"],
                messages=messages,
                max_tokens=tokens_budget,
                temperature=temperature,
                api_key=config.get("api_key"),
                api_base=route["api_base"] if route else config.get("api_base"),
                timeout=DEFAULT_TIMEOUT,
                extra_headers=headers,
            )
            _on_protocol_success(route)
            content = response.choices[0].message.content

            # Reasoning models can burn the whole output budget on
            # reasoning, returning empty content with no exception.
            # Retry with a much larger budget instead of failing silently.
            if not (content and content.strip()) and attempt < max_retries:
                tokens_budget = max(tokens_budget * 4, 2000)
                logger.warning(
                    f"[AI_LIB] Empty content from {config['model']} "
                    f"(likely reasoning consumed max_tokens={max_tokens}) — "
                    f"retrying with {tokens_budget} (attempt {attempt + 1}/{max_retries + 1})"
                )
                continue

            if usage_out is not None:
                _u = getattr(response, "usage", None)
                usage_out["router"] = usage_out.get("router", 0) + int(
                    getattr(_u, "total_tokens", 0) or 0
                )
                usage_out["router_prompt"] = usage_out.get("router_prompt", 0) + int(
                    getattr(_u, "prompt_tokens", 0) or 0
                )
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
            last_error = e
            protocol_error = _is_ladder_error(e)
            if not protocol_error:
                logger.error(f"[AI_LIB] Error calling LLM ({config['model']}): {e}")
                return None
        if protocol_error:
            ladder_error = last_error
            break

    # Runtime fallback: walk the protocol ladder for multi-surface gateways.
    if route is not None and ladder_error is not None:
        for alt in _protocol_sequence(route)[1:]:
            step = _target_for(route, alt)
            _log_protocol_retry(ladder_error, step["model"], alt)
            try:
                response = completion(
                    model=step["model"],
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    api_key=config.get("api_key"),
                    api_base=step["api_base"],
                    timeout=DEFAULT_TIMEOUT,
                    extra_headers=headers,
                )
                _on_protocol_success(step)
                content = response.choices[0].message.content
                return content.strip() if content else None
            except Exception as e2:
                logger.warning(
                    f"[AI_LIB] Ladder retry also failed on {step['model']} "
                    f"({type(e2).__name__}: {e2})"
                )
    elif ladder_error is None:
        logger.error(f"[AI_LIB] Error calling LLM ({config['model']}) — unknown failure")
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
    session_id: str | None = None,
) -> Generator[str, None, None]:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    route, headers = _resolve_route(config, session_id)
    max_tokens = _floor_max_tokens(route, max_tokens)

    try:
        response = completion(
            model=route["model"] if route else config["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            api_key=config.get("api_key"),
            api_base=route["api_base"] if route else config.get("api_base"),
            timeout=DEFAULT_TIMEOUT,
            extra_headers=headers,
        )
        for chunk in response:
            content = chunk.choices[0].delta.content if chunk.choices else None
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
    session_id: str | None = None,
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

    route, headers = _resolve_route(config, session_id)
    max_tokens = _floor_max_tokens(route, max_tokens)

    base_kwargs = {
        "messages": messages,
        "tools": tools,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "api_key": config.get("api_key"),
        "timeout": DEFAULT_TIMEOUT,
        "extra_headers": headers,
    }

    # Only add tool_choice if the caller explicitly requested it.
    # litellm.drop_params=True removes the parameter if the provider doesn't support it.
    if tool_choice is not None:
        base_kwargs["tool_choice"] = tool_choice

    try:
        response = completion(
            model=route["model"] if route else config["model"],
            api_base=route["api_base"] if route else config.get("api_base"),
            **base_kwargs,
        )
        _on_protocol_success(route)
        return response
    except Exception as e:
        if route is not None and _is_ladder_error(e):
            for alt in _protocol_sequence(route)[1:]:
                step = _target_for(route, alt)
                _log_protocol_retry(e, step["model"], alt)
                try:
                    response = completion(
                        model=step["model"], api_base=step["api_base"], **base_kwargs
                    )
                    _on_protocol_success(step)
                    return response
                except Exception as e2:
                    logger.warning(
                        f"[AI_LIB] Ladder retry also failed on {step['model']} "
                        f"({type(e2).__name__}: {e2})"
                    )
                    if not _is_ladder_error(e2):
                        break
        else:
            logger.error(f"[AI_LIB] Error calling LLM with tools ({config.get('model')}): {e}")
        return None


def call_llm_messages_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_choice: str | dict | None = "auto",
    model: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.2,
    usage: LLMUsage = "routing",
    session_id: str | None = None,
):
    """
    Tool-calling over a full message list (multi-turn agent loop).

    `messages` must already include system/history/user/tool roles.
    Returns the raw response or None on failure.
    """
    config = _get_model_config(usage)
    if model:
        config["model"] = model

    route, headers = _resolve_route(config, session_id)
    max_tokens = _floor_max_tokens(route, max_tokens)

    base_kwargs = {
        "messages": messages,
        "tools": tools,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "api_key": config.get("api_key"),
        "timeout": DEFAULT_TIMEOUT,
        "extra_headers": headers,
    }
    if tool_choice is not None:
        base_kwargs["tool_choice"] = tool_choice

    try:
        response = completion(
            model=route["model"] if route else config["model"],
            api_base=route["api_base"] if route else config.get("api_base"),
            **base_kwargs,
        )
        _on_protocol_success(route)
        return response
    except Exception as e:
        if route is not None and _is_ladder_error(e):
            for alt in _protocol_sequence(route)[1:]:
                step = _target_for(route, alt)
                _log_protocol_retry(e, step["model"], alt)
                try:
                    response = completion(
                        model=step["model"], api_base=step["api_base"], **base_kwargs
                    )
                    _on_protocol_success(step)
                    return response
                except Exception as e2:
                    logger.warning(
                        f"[AI_LIB] Ladder retry also failed on {step['model']} "
                        f"({type(e2).__name__}: {e2})"
                    )
                    if not _is_ladder_error(e2):
                        break
        else:
            logger.error(f"[AI_LIB] Error calling LLM loop with tools ({config.get('model')}): {e}")
        return None


# ------------------------------------------------------------------
# Streaming with message history (typed deltas: answer / thinking)
# ------------------------------------------------------------------

def stream_llm_deltas(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
    usage: LLMUsage = "chatbot",
    auto_continue: int = 0,
    session_id: str | None = None,
) -> Generator[tuple[str, str], None, None]:
    """
    Streams a completion as typed deltas:
      ("thinking", text) — provider reasoning_content (None em modelos sem thinking)
      ("answer",   text) — conteúdo final da resposta
      ("error",    text) — terminal event, orienta APENAS quando nada foi gerado:
                   chamador decide como sinalizar (chamadores de chat ignoram)

    Auto-continuation: if the model hits the output cap (finish_reason
    == "length"), up to `auto_continue` extra calls append the partial
    answer and continue seamlessly.

    Multi-surface gateways fall through the protocol ladder on the first
    (token-less) attempt failure.

    Never raises network errors materially — errors are logged and the
    stream simply ends (callers persist what they got).
    """
    config = _get_model_config(usage)
    if model:
        config["model"] = model

    route, headers = _resolve_route(config, session_id)
    max_tokens = _floor_max_tokens(route, max_tokens)

    # Streaming capability diagnostics: warn (once per model/process) when
    # the tier model can't produce progressive tokens, so a "whole answer
    # arrives at the end" report is diagnosed in one glance.
    if route is not None and route["bare"].lower() not in _stream_style_warned:
        style = model_routing.stream_style(route["bare"], route["base_api_url"])
        _stream_style_warned.add(route["bare"].lower())
        if style == "burst":
            logger.warning(
                f"[AI_LIB] '{route['bare']}' é um burst-streamer: o gateway bufferiza "
                f"a geração completa e devolve tudo de uma vez — a resposta do chat "
                f"não aparecerá progressivamente (prefira um modelo genuine-streaming "
                f"neste tier, ex. glm/deepseek/mimo)."
            )
        elif style == "pseudo":
            logger.warning(
                f"[AI_LIB] '{route['bare']}' não faz streaming (pseudo-stream): "
                f"uma única chamada não-streaming será feita em fallback."
            )

    active_messages = list(messages)
    remaining_continue = max(0, int(auto_continue))

    # Ladder state: only run while nothing has streamed yet. Once a token
    # reached the client the surface clearly works, so errors are terminal.
    ladder = _protocol_sequence(route)
    ladder_idx = 0
    streamed_anything = False
    fallback_tried = False
    tokens_budget = max_tokens
    empty_retries = 0
    final_error: str | None = None

    while True:
        partial_answer = ""
        finish_reason = None
        error = None
        try:
            call_kwargs = {
                "model": (
                    _target_for(route, ladder[ladder_idx])["model"]
                    if route else config["model"]
                ),
                "messages": active_messages,
                "max_tokens": tokens_budget,
                "temperature": temperature,
                "stream": True,
                "api_key": config.get("api_key"),
                "api_base": (
                    _target_for(route, ladder[ladder_idx])["api_base"]
                    if route else config.get("api_base")
                ),
                "timeout": DEFAULT_TIMEOUT,
                "extra_headers": headers,
            }
            if route is None or route["protocol"] == "chat":
                call_kwargs["stream_options"] = {"include_usage": True}
            response = completion(**call_kwargs)
            for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", None)
                    reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                    if content:
                        streamed_anything = True
                        partial_answer += content
                        yield ("answer", content)
                    if reasoning:
                        yield ("thinking", reasoning)
                    fr = getattr(chunk.choices[0], "finish_reason", None)
                    if fr:
                        finish_reason = fr
        except GeneratorExit:
            # Client disconnected — strictly stop (no auto-continue calls).
            raise
        except Exception as e:
            error = e
            logger.error(f"[AI_LIB] Streaming error ({config.get('model')}): {e}")

        if error is not None:
            stepped = False
            if route is not None and not streamed_anything:
                for alt in ladder[ladder_idx + 1:]:
                    step = _target_for(route, alt)
                    _log_protocol_retry(error, step["model"], alt)
                    try:
                        call_kwargs = {
                            "model": step["model"],
                            "messages": active_messages,
                            "max_tokens": tokens_budget,
                            "temperature": temperature,
                            "stream": True,
                            "api_key": config.get("api_key"),
                            "api_base": step["api_base"],
                            "timeout": DEFAULT_TIMEOUT,
                            "extra_headers": headers,
                        }
                        if step["protocol"] == "chat":
                            call_kwargs["stream_options"] = {"include_usage": True}
                        response = completion(**call_kwargs)
                        ladder_idx = ladder.index(alt)
                        _on_protocol_success(step)
                        streamed_anything = True
                        for chunk in response:
                            if chunk.choices:
                                delta = chunk.choices[0].delta
                                content = getattr(delta, "content", None)
                                reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                                if content:
                                    partial_answer += content
                                    yield ("answer", content)
                                if reasoning:
                                    yield ("thinking", reasoning)
                                fr = getattr(chunk.choices[0], "finish_reason", None)
                                if fr:
                                    finish_reason = fr
                        error = None
                        stepped = True
                        break
                    except GeneratorExit:
                        raise
                    except Exception as e2:
                        logger.warning(
                            f"[AI_LIB] Ladder retry also failed on {step['model']} "
                            f"({type(e2).__name__}: {e2})"
                        )
                        if not _is_ladder_error(e2):
                            break
                        error = e2
        if error is not None and not stepped:
            final_error = f"{type(error).__name__}: {error}"
            break

        # Pseudo-stream fallback: some gateways/models answer stream requests
        # with a single empty delta (no content at all). When nothing was
        # streamed, retry once non-streaming on the current surface; if that
        # also fails with a ladder-able error, walk the remaining ladder.
        if not partial_answer and error is None and not fallback_tried:
            fallback_tried = True
            nonstream_kwargs = dict(call_kwargs)
            nonstream_kwargs.pop("stream", None)
            nonstream_kwargs.pop("stream_options", None)
            attempts = [(ladder[ladder_idx], nonstream_kwargs)]
            if route is not None:
                for alt in ladder[ladder_idx + 1:]:
                    step = _target_for(route, alt)
                    nonstream_kwargs = dict(nonstream_kwargs)
                    nonstream_kwargs["model"] = step["model"]
                    nonstream_kwargs["api_base"] = step["api_base"]
                    attempts.append((alt, nonstream_kwargs))
            for alt, kw in attempts:
                try:
                    nresp = completion(**kw)
                    msg = nresp.choices[0].message
                    content = getattr(msg, "content", None)
                    reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
                    if reasoning:
                        yield ("thinking", reasoning)
                    if content:
                        streamed_anything = True
                        if alt != ladder[ladder_idx]:
                            _on_protocol_success(_target_for(route, alt))
                        partial_answer += content
                        finish_reason = None
                        yield ("answer", content)
                        break
                except Exception as e2:
                    if not _is_ladder_error(e2, include_timeout=True):
                        logger.warning(
                            f"[AI_LIB] Non-stream fallback aborted ({config['model']}/{alt}): {e2}"
                        )
                        break
                    logger.warning(
                        f"[AI_LIB] Non-stream fallback failed ({config['model']}/{alt}) — walking ladder"
                    )

        truncated = finish_reason == "length" and partial_answer.strip()
        if not (truncated and remaining_continue > 0):
            # Reasoning models can burn the whole output budget on
            # reasoning and end the stream with no visible content and
            # no exception — retry with a much larger budget instead of
            # surfacing an empty answer (mirrors call_llm's escalation).
            if not partial_answer and error is None and empty_retries < 2:
                empty_retries += 1
                tokens_budget = max(tokens_budget * 4, 2000)
                logger.warning(
                    f"[AI_LIB] Stream ended with no content from {config['model']} "
                    f"(likely reasoning consumed max_tokens={max_tokens}) — "
                    f"retrying with {tokens_budget} (empty attempt {empty_retries})"
                )
                continue
            break

        remaining_continue -= 1
        active_messages = active_messages + [
            {"role": "assistant", "content": partial_answer},
            {
                "role": "user",
                "content": "Continue exatamente de onde parou — não repita nada já escrito, sem novo preâmbulo.",
            },
        ]
        logger.info(f"[AI_LIB] Output cap atingido — auto-continuação ({remaining_continue} restantes)")

    if not streamed_anything:
        msg = final_error or (
            f"model returned no content ({config.get('model')})"
        )
        logger.error(f"[AI_LIB] Streaming ended empty ({config['model']}): {msg}")
        yield ("error", msg)


def stream_llm_response(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
    usage: LLMUsage = "chatbot",
    session_id: str | None = None,
) -> Generator[str, None, None]:
    """Legacy compatibility wrapper — plain answer text only."""
    for kind, text in stream_llm_deltas(
        messages, model, max_tokens, temperature, usage, session_id=session_id
    ):
        if kind == "answer":
            yield text


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
    session_id: str | None = None,
) -> str | None:
    config = _get_model_config(usage)

    if model:
        config["model"] = model

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    route, headers = _resolve_route(config, session_id)
    max_tokens = _floor_max_tokens(route, max_tokens)

    ladder_error = None

    for attempt in range(max_retries + 1):
        try:
            response = await acompletion(
                model=route["model"] if route else config["model"],
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=config.get("api_key"),
                api_base=route["api_base"] if route else config.get("api_base"),
                timeout=DEFAULT_TIMEOUT,
                extra_headers=headers,
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
            if route is not None and _is_ladder_error(e):
                ladder_error = e
                break
            logger.error(f"[AI_LIB] Error calling LLM async ({config['model']}): {e}")
            return None

    if route is not None and ladder_error is not None:
        # Runtime fallback: walk the protocol ladder.
        for alt in _protocol_sequence(route)[1:]:
            step = _target_for(route, alt)
            _log_protocol_retry(ladder_error, step["model"], alt)
            try:
                response = await acompletion(
                    model=step["model"],
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    api_key=config.get("api_key"),
                    api_base=step["api_base"],
                    timeout=DEFAULT_TIMEOUT,
                    extra_headers=headers,
                )
                _on_protocol_success(step)
                content = response.choices[0].message.content
                return content.strip() if content else None
            except Exception as e2:
                logger.warning(
                    f"[AI_LIB] Ladder retry also failed on {step['model']} "
                    f"({type(e2).__name__}: {e2})"
                )
                if not _is_ladder_error(e2):
                    break
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
