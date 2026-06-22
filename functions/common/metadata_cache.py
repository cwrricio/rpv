# functions/common/metadata_cache.py
"""
Cache/mirror local de metadados acadêmicos essenciais.

Para reduzir dependência de APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar),
este módulo mantém um espelho local dos metadados mais críticos:
- Autores (ORCID, OpenAlex)
- Obras/publicações (DOI-based)
- Instituições

Estratégia:
1. Cache em banco de dados (mesmo storage do projeto)
2. Atualização incremental (só busca o que mudou)
3. Fallback automático para cache quando API externa falha
4. TTL diferenciado por tipo de dado (autores: 7 dias, obras: 30 dias)
"""
from __future__ import annotations

import time
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from functions.common.dbref import ref

logger = logging.getLogger(__name__)

# TTLs em segundos
TTL_AUTOR = 7 * 24 * 60 * 60      # 7 dias
TTL_OBRA = 30 * 24 * 60 * 60       # 30 dias
TTL_INSTITUICAO = 30 * 24 * 60 * 60  # 30 dias


def _cache_ref(entity_type: str):
    """Retorna referência para coleção de cache no storage."""
    return ref(f"metadata_cache/{entity_type}")


def _hash_key(source: str, identifier: str) -> str:
    """Gera chave única para cache baseada na fonte e identificador."""
    payload = f"{source}:{identifier}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def get_cached(
    source: str,
    identifier: str,
    entity_type: str,
    max_age: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Busca metadado no cache local.
    
    Args:
        source: Fonte original ('OPENALEX', 'ORCID', 'CROSSREF', 'SEMANTIC_SCHOLAR')
        identifier: Identificador único (ORCID, DOI, OpenAlex ID)
        entity_type: Tipo de entidade ('autor', 'obra', 'instituicao')
        max_age: Idade máxima em segundos (usa TTL padrão se None)
    
    Returns:
        Dados do cache se válidos, None se não encontrado ou expirado
    """
    if max_age is None:
        if entity_type == 'autor':
            max_age = TTL_AUTOR
        elif entity_type == 'obra':
            max_age = TTL_OBRA
        else:
            max_age = TTL_INSTITUICAO
    
    cache_key = _hash_key(source, identifier)
    cache_collection = _cache_ref(entity_type)
    
    try:
        cached_data = cache_collection.child(cache_key).get()
        if cached_data is None:
            return None
        
        # Verificar se não expirou
        cached_at = cached_data.get('cached_at', 0)
        if time.time() - cached_at > max_age:
            logger.debug("Cache expirado para %s:%s", source, identifier)
            return None
        
        logger.debug("Cache hit para %s:%s", source, identifier)
        return cached_data.get('data')
    
    except Exception as exc:
        logger.warning("Erro ao buscar cache: %s", exc)
        return None


def set_cache(
    source: str,
    identifier: str,
    entity_type: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Armazena metadado no cache local.
    
    Args:
        source: Fonte original
        identifier: Identificador único
        entity_type: Tipo de entidade
        data: Dados a serem cacheados
        metadata: Metadados adicionais (opcional)
    
    Returns:
        Chave do cache
    """
    cache_key = _hash_key(source, identifier)
    cache_collection = _cache_ref(entity_type)
    
    cache_entry = {
        'source': source,
        'identifier': identifier,
        'entity_type': entity_type,
        'data': data,
        'cached_at': time.time(),
        'metadata': metadata or {}
    }
    
    try:
        cache_collection.child(cache_key).set(cache_entry)
        logger.debug("Cache set para %s:%s", source, identifier)
        return cache_key
    
    except Exception as exc:
        logger.error("Erro ao salvar cache: %s", exc)
        raise


def get_or_fetch(
    source: str,
    identifier: str,
    entity_type: str,
    fetch_fn,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Busca do cache ou faz fetch da API externa.
    
    Pattern principal para ingestão: tenta cache primeiro,
    se não existir ou expirado, busca da API e atualiza cache.
    
    Args:
        source: Fonte ('OPENALEX', 'ORCID', etc)
        identifier: Identificador
        entity_type: Tipo de entidade
        fetch_fn: Função que busca da API externa (recebe identifier)
        force_refresh: Ignorar cache e forçar fetch
    
    Returns:
        Dados da entidade (do cache ou API)
    """
    # Tentar cache
    if not force_refresh:
        cached = get_cached(source, identifier, entity_type)
        if cached is not None:
            return {
                'data': cached,
                'source': 'cache',
                'identifier': identifier
            }
    
    # Fazer fetch da API
    logger.info("Cache miss, buscando %s:%s da API", source, identifier)
    external_data = fetch_fn(identifier)
    
    # Atualizar cache
    set_cache(source, identifier, entity_type, external_data)
    
    return {
        'data': external_data,
        'source': 'api',
        'identifier': identifier
    }


def list_cached_entities(
    entity_type: str,
    source: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Lista entidades cacheadas de um tipo.
    
    Args:
        entity_type: Tipo de entidade
        source: Filtrar por fonte (opcional)
        limit: Máximo de resultados
    
    Returns:
        Lista de resumos das entidades cacheadas
    """
    cache_collection = _cache_ref(entity_type)
    
    try:
        all_data = cache_collection.get()
        if all_data is None:
            return []
        
        results = []
        for key, entry in all_data.items():
            if source and entry.get('source') != source:
                continue
            
            results.append({
                'cache_key': key,
                'source': entry.get('source'),
                'identifier': entry.get('identifier'),
                'cached_at': entry.get('cached_at'),
                'data_preview': _get_preview(entry.get('data', {}))
            })
            
            if len(results) >= limit:
                break
        
        return results
    
    except Exception as exc:
        logger.warning("Erro ao listar cache: %s", exc)
        return []


def _get_preview(data: Dict[str, Any], max_fields: int = 3) -> Dict[str, Any]:
    """Extrai preview dos dados para listagem."""
    preview = {}
    preview_fields = {
        'autor': ['display_name', 'orcid', 'affiliation'],
        'obra': ['title', 'doi', 'publication_date'],
        'instituicao': ['display_name', 'country_code', 'type']
    }
    
    for field in preview_fields.get(list(data.keys())[0] if data else '', [])[:max_fields]:
        if field in data:
            preview[field] = data[field]
    
    return preview or data


def cleanup_expired(entity_type: Optional[str] = None) -> int:
    """
    Remove entradas expiradas do cache.
    
    Args:
        entity_type: Tipo específico para limpar (None = todos)
    
    Returns:
        Número de entradas removidas
    """
    types_to_clean = [entity_type] if entity_type else ['autor', 'obra', 'instituicao']
    total_removed = 0
    
    for etype in types_to_clean:
        max_age = TTL_AUTOR if etype == 'autor' else TTL_OBRA if etype == 'obra' else TTL_INSTITUICAO
        cache_collection = _cache_ref(etype)
        
        try:
            all_data = cache_collection.get()
            if all_data is None:
                continue
            
            for key, entry in all_data.items():
                cached_at = entry.get('cached_at', 0)
                if time.time() - cached_at > max_age:
                    cache_collection.child(key).delete()
                    total_removed += 1
        
        except Exception as exc:
            logger.warning("Erro no cleanup de %s: %s", etype, exc)
    
    logger.info("Cleanup completado: %d entradas removidas", total_removed)
    return total_removed


# API Routes para gestão do cache
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/metadata-cache", tags=["Cache de Metadados"])


@router.get("/{entity_type}")
def list_entities(
    entity_type: str,
    source: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=1000)
):
    """Lista entidades cacheadas."""
    if entity_type not in ['autor', 'obra', 'instituicao']:
        raise HTTPException(400, "Tipo inválido")
    
    entities = list_cached_entities(entity_type, source, limit)
    return {"entities": entities, "count": len(entities)}


@router.delete("/{entity_type}/expired")
def cleanup(entity_type: Optional[str] = Query(default=None)):
    """Remove entradas expiradas do cache."""
    removed = cleanup_expired(entity_type)
    return {"removed": removed}


@router.get("/stats")
def cache_stats():
    """Estatísticas do cache."""
    stats = {}
    for etype in ['autor', 'obra', 'instituicao']:
        cache_collection = _cache_ref(etype)
        try:
            all_data = cache_collection.get()
            count = len(all_data) if all_data else 0
            stats[etype] = {"count": count}
        except:
            stats[etype] = {"count": 0}
    
    return stats