# functions/workers/incremental_update.py
"""
Worker de atualização incremental do cache de metadados.

Este worker é responsável por:
1. Identificar metadados que precisam ser atualizados (baseado em TTL)
2. Buscar atualizações das APIs externas
3. Manter mirror local sincronizado
4. Reportar métricas de atualização

Execução agendada: diária (2h da manhã)
"""
import time
import logging
from typing import List, Dict
from functions.common import metadata_cache
from functions.common import http_client
from functions.common.dbref import ref

logger = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
ORCID_API = "https://pub.orcid.org/v3.0"


def fetch_author_from_openalex(openalex_id: str) -> Dict:
    """Busca autor do OpenAlex."""
    url = f"{OPENALEX_API}/authors/{openalex_id}"
    return http_client.get(url, timeout=30)


def fetch_author_from_orcid(orcid_id: str) -> Dict:
    """Busca autor do ORCID."""
    url = f"{ORCID_API}/{orcid_id}"
    headers = {"Accept": "application/json"}
    return http_client.get(url, headers=headers, timeout=30)


def fetch_work_by_doi(doi: str) -> Dict:
    """Busca obra por DOI no OpenAlex."""
    # DOI precisa ser URL-encoded
    encoded_doi = doi.replace("/", "%2F")
    url = f"{OPENALEX_API}/works/{encoded_doi}"
    return http_client.get(url, timeout=30)


def update_expired_cache():
    """
    Atualiza entradas de cache expiradas.
    
    Estratégia:
    1. Listar todas as entradas de cache
    2. Identificar as expiradas
    3. Tentar atualizar da API externa
    4. Se API falhar, manter cache expirado (fallback) e logar warning
    """
    stats = {
        'total_checked': 0,
        'expired': 0,
        'updated': 0,
        'failed': 0,
        'fallback': 0
    }
    
    for entity_type in ['autor', 'obra', 'instituicao']:
        logger.info("Verificando cache expirado para: %s", entity_type)
        cached_entities = metadata_cache.list_cached_entities(entity_type, limit=500)
        
        for entry in cached_entities:
            stats['total_checked'] += 1
            
            # Verificar se expirou
            cached_at = entry.get('cached_at', 0)
            max_age = (
                metadata_cache.TTL_AUTOR if entity_type == 'autor'
                else metadata_cache.TTL_OBRA if entity_type == 'obra'
                else metadata_cache.TTL_INSTITUICAO
            )
            
            if time.time() - cached_at < max_age:
                continue  # Não expirou
            
            stats['expired'] += 1
            source = entry.get('source')
            identifier = entry.get('identifier')
            
            logger.info(
                "Atualizando %s:%s (expirado há %.1f dias)",
                source, identifier, (time.time() - cached_at) / 86400
            )
            
            try:
                # Tentar atualização baseada no tipo
                if entity_type == 'autor':
                    if source == 'OPENALEX':
                        new_data = fetch_author_from_openalex(identifier)
                    elif source == 'ORCID':
                        new_data = fetch_author_from_orcid(identifier)
                    else:
                        continue
                
                elif entity_type == 'obra':
                    if source == 'OPENALEX':
                        new_data = fetch_work_by_doi(identifier)
                    else:
                        continue
                else:
                    continue
                
                # Atualizar cache
                metadata_cache.set_cache(source, identifier, entity_type, new_data)
                stats['updated'] += 1
                logger.debug("Atualizado com sucesso: %s:%s", source, identifier)
            
            except Exception as exc:
                logger.warning(
                    "Falha ao atualizar %s:%s - %s. Mantendo cache expirado.",
                    source, identifier, exc
                )
                stats['failed'] += 1
                
                # Manter cache expirado como fallback (não fazer nada)
                # O cache expirado ainda pode ser usado em caso de indisponibilidade da API
    
    logger.info(
        "Atualização incremental completada: "
        "verificados=%d, expirados=%d, atualizados=%d, falhas=%d",
        stats['total_checked'], stats['expired'], stats['updated'], stats['failed']
    )
    
    return stats


def warm_up_cache():
    """
    Pré-aquece cache com metadados críticos.
    
    Útil para executar após deploy ou manutenção.
    Busca os metadados mais acessados recentemente.
    """
    logger.info("Iniciando warm-up do cache")
    
    # Buscar provenance para identificar items mais acessados
    prov_ref = ref("provenance")
    try:
        prov_data = prov_ref.get()
        if not prov_data:
            logger.info("Nenhum dado de provenance para warm-up")
            return {'warmed': 0}
        
        # Ordenar por createdAt e pegar últimos
        batches = sorted(
            prov_data.items(),
            key=lambda x: x[1].get('createdAt', 0) if isinstance(x[1], dict) else 0,
            reverse=True
        )[:10]  # Últimos 10 batches
        
        warmed = 0
        for batch_id, batch_data in batches:
            # Buscar items do batch
            staging_ref = ref(f"staging/import_batches/{batch_id}/items")
            items = staging_ref.get()
            if not items:
                continue
            
            for item_key, item_data in list(items.items())[:5]:  # 5 items por batch
                if not isinstance(item_data, dict):
                    continue
                
                source = item_data.get('source')
                raw = item_data.get('raw', {})
                
                if source == 'OPENALEX':
                    # Cache da obra
                    work_id = raw.get('id', '').replace('https://openalex.org/', '')
                    if work_id:
                        try:
                            metadata_cache.set_cache('OPENALEX', work_id, 'obra', raw)
                            warmed += 1
                        except Exception as exc:
                            logger.warning("Erro no warm-up: %s", exc)
        
        logger.info("Warm-up completado: %d itens em cache", warmed)
        return {'warmed': warmed}
    
    except Exception as exc:
        logger.error("Erro no warm-up: %s", exc)
        return {'error': str(exc), 'warmed': 0}


# Endpoint FastAPI para triggers manuais
from fastapi import APIRouter

router = APIRouter(prefix="/workers/incremental-update", tags=["Workers"])


@router.post("/run")
def run_update():
    """Executa atualização incremental do cache."""
    stats = update_expired_cache()
    return stats


@router.post("/warm-up")
def run_warm_up():
    """Executa warm-up do cache."""
    result = warm_up_cache()
    return result