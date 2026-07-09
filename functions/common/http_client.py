# functions/common/http_client.py
"""
Cliente HTTP unificado para APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar).

Fornece timeout configurável, retry com backoff exponencial e cache em memória
com TTL. Todos os módulos de ingestão devem usar este cliente em vez de
`requests.get` diretamente — isso garante resiliência uniforme e evita que uma
falha pontual de API derrube o fluxo inteiro.
"""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional
from functools import lru_cache

import requests
from requests import Response

logger = logging.getLogger(__name__)

# Valores-padrão usados quando não sobrescritos na chamada.
DEFAULT_TIMEOUT = 30          # segundos
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5         # fator multiplicativo entre tentativas
DEFAULT_CACHE_TTL = 300       # segundos (5 min)


class _CacheEntry:
    __slots__ = ("data", "expires_at")

    def __init__(self, data: Any, ttl: float) -> None:
        self.data = data
        self.expires_at = time.monotonic() + ttl


_cache: Dict[str, _CacheEntry] = {}


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and time.monotonic() < entry.expires_at:
        return entry.data
    _cache.pop(key, None)
    return None


def _cache_set(key: str, data: Any, ttl: float) -> None:
    _cache[key] = _CacheEntry(data, ttl)


def _build_cache_key(url: str, params: Optional[Dict]) -> str:
    import hashlib, json
    payload = json.dumps({"url": url, "params": params or {}}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def get(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    cache_ttl: float = DEFAULT_CACHE_TTL,
    expected_status: int = 200,
) -> Dict[str, Any]:
    """Realiza GET com retry, backoff e cache em memória.

    Lança `requests.HTTPError` se o status não for o esperado após todas as
    tentativas. Lança `requests.Timeout` / `requests.ConnectionError` em falha
    de rede persistente.
    """
    cache_key = _build_cache_key(url, params)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("cache hit: %s", url)
        return cached

    last_exc: Exception | None = None
    delay = 1.0

    for attempt in range(1, retries + 1):
        try:
            resp: Response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
            if resp.status_code != expected_status:
                resp.raise_for_status()
            data = resp.json()
            if cache_ttl > 0:
                _cache_set(cache_key, data, cache_ttl)
            return data
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            logger.warning("tentativa %d/%d falhou (%s): %s", attempt, retries, url, exc)
        except requests.HTTPError as exc:
            # erros 4xx não devem ser retentados
            raise exc from exc

        if attempt < retries:
            time.sleep(delay)
            delay *= backoff

    raise last_exc  # type: ignore[misc]


def clear_cache() -> None:
    """Limpa todo o cache (útil em testes)."""
    _cache.clear()
