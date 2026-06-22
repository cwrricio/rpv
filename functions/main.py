# functions/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# 1) Carrega .env o mais cedo possível
load_dotenv()

from config.settings import settings

_backend = (settings.STORAGE_BACKEND or "firebase").lower()

# 2) Inicializa o Firebase apenas quando ele é o backend ativo.
#    Com STORAGE_BACKEND=postgres a aplicação sobe sem qualquer credencial Google.
if _backend == "firebase":
    from config.firebase_admin_init import init_firebase
    init_firebase()
elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    import warnings
    warnings.warn(
        "GOOGLE_APPLICATION_CREDENTIALS está definida mas STORAGE_BACKEND=postgres. "
        "A credencial Google não será usada. Remova-a do ambiente para evitar confusão.",
        stacklevel=1,
    )

# Camada de Aplicação: lógica de métricas extraída deste arquivo (Frente 4.1/4.2)
from functions.services.analytics import compute_author_metrics

# 3) Cria a app UMA vez
app = FastAPI(title="PosGrad Board (Python + RTDB)")

# ---------------------------------------------------------------------------
# CORS — origens configuradas via variável de ambiente CORS_ORIGINS
# Defina no .env (separadas por vírgula), ex.:
#   CORS_ORIGINS=http://localhost:5173,https://meu-app.web.app
# Se a variável não estiver definida, usa apenas o localhost de desenvolvimento.
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("CORS_ORIGINS", "")
if _raw_origins.strip():
    allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    allow_origin_regex = None
else:
    # Fallback seguro para desenvolvimento local: aceita localhost em qualquer porta
    allow_origins = []
    allow_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _without_id(item: dict) -> dict:
    return {k: v for k, v in item.items() if k != "id"}


def _storage_collection(path_root: str) -> dict:
    """Retorna uma colecao no formato historico do RTDB: {id: payload}."""
    from functions.adapters import get_storage

    return {
        item["id"]: _without_id(item)
        for item in get_storage().list(path_root)
        if isinstance(item, dict) and item.get("id")
    }


def _storage_item(path_root: str, item_id: str):
    """Le um item pela porta ativa, sem expor a API concreta do banco."""
    from functions.adapters import get_storage

    item = get_storage().get(path_root, item_id)
    return _without_id(item) if item else None


def _legacy_storage_get(path: str):
    """
    Compatibilidade interna: le pelo StoragePort ativo.
    Mantem paths historicos no formato "colecao/id".
    """
    try:
        # Compatibility path for older callers inside this module.
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return {}
        if len(parts) == 1:
            return _storage_collection(parts[0])
        return _storage_item(parts[0], parts[1]) or {}
    except Exception as e:
        import traceback
        print(f"Erro ao acessar storage ({path}): {str(e)}")
        traceback.print_exc()
        raise e

# 4) Endpoints básicos
@app.get("/", summary="Root")
def root():
    return {"status": "API rodando 🚀"}

@app.get("/health", summary="Health")
def health():
    checks: dict = {"backend": _backend, "db": "ok"}
    if _backend == "postgres":
        try:
            from functions.adapters import get_storage
            storage = get_storage()
            # Testa conectividade com uma leitura vazia na coleção sentinel.
            storage.list("_health_check")
        except Exception as exc:
            checks["db"] = f"error: {exc}"
            raise HTTPException(status_code=503, detail=checks)
    return {"ok": True, **checks}

@app.get("/autores_flat", summary="Colecao autores_flat")
def autores_flat():
    try:
        data = _storage_collection("autores_flat")
        return data or {}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage error: {e}")

@app.get("/autores_flat/{author_id}", summary="Autor em autores_flat/{id}")
def autores_flat_item(author_id: str):
    try:
        data = _storage_item("autores_flat", author_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Autor não encontrado")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage error: {e}")

@app.get("/autores/{author_id}/metrics", summary="Agrega métricas a partir de autores_flat.{id}.works")
def author_metrics(author_id: str):
    """
    Agrega métricas a partir do nó autores_flat/<id>/works:
    - publications_count, total_citations, h_index, h5_index, i10_index
    - first_year, last_year
    - top_concepts (lista [concept, count]) e top_coauthors (lista [name,count])
    - sample_publications (até 10 itens)

    A regra de negócio vive em services/analytics.compute_author_metrics();
    o handler apenas lê o nó do banco e trata o 404.
    """
    try:
        node = _storage_item("autores_flat", author_id)
        if not node:
            raise HTTPException(status_code=404, detail="Autor não encontrado")
        return compute_author_metrics(author_id, node)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage error: {e}")

# 5) Importa e registra todos os routers (prefixos apenas aqui!)
from functions.api_routes.docentes import router as docentes_router
from functions.api_routes.discentes import router as discentes_router
from functions.api_routes.linhas import router as linhas_router
from functions.api_routes.projetos import router as projetos_router
from functions.api_routes.veiculos import router as veiculos_router
from functions.api_routes.produtos import router as produtos_router

from functions.ingest.openalex_orcid import router as openalex_orcid_router
from functions.ingest.openalex_name import router as openalex_name_router
from functions.ingest.openalex_ingest_only import router as openalex_ingest_only_router
from functions.api_routes.processamento_openalex import router as processamento_openalex_router
from functions.api_routes.autores import router as autores_router
from functions.api_routes.autores_links import router as autores_links_router
from functions.api_routes.autores_generate import router as autores_generate_router

from functions.ingest.orcid_api import router as orcid_router
from functions.ingest.crossref_api import router as crossref_router
from functions.ingest.semanticscholar_api import router as s2_router
from functions.api_routes.autores_merge import router as autores_merge_router
from functions.api_routes.harvest_authors import router as harvest_authors_router
from functions.api_routes.autores_flat import router as autores_flat_router
from functions.api_routes.jobs import router as jobs_router
from functions.api_routes.auth import router as auth_router


# OBS: nos módulos *não* use prefix= no APIRouter; deixe só @router.get("/") etc.
app.include_router(docentes_router,               prefix="/docentes")
app.include_router(discentes_router,              prefix="/discentes")
app.include_router(linhas_router,                 prefix="/linhas")
app.include_router(projetos_router,               prefix="/projetos")
app.include_router(veiculos_router,               prefix="/veiculos")
app.include_router(produtos_router,               prefix="/produtos")
app.include_router(autores_router,                prefix="/autores")
app.include_router(autores_links_router)  # sem prefix extra (já tem caminhos completos)
app.include_router(autores_generate_router)  # sem prefix extra

app.include_router(orcid_router)
app.include_router(crossref_router)
app.include_router(s2_router)
app.include_router(autores_merge_router)
app.include_router(harvest_authors_router)
app.include_router(autores_flat_router)
app.include_router(jobs_router)
app.include_router(auth_router)


app.include_router(openalex_orcid_router,         prefix="/ingest/openalex-orcid")
app.include_router(openalex_name_router,          prefix="/ingest/openalex-name")
app.include_router(openalex_ingest_only_router,   prefix="/ingest/openalex")
app.include_router(processamento_openalex_router, prefix="/processamento/openalex")

# 6) Loga as rotas ao iniciar (ajuda no debug)
@app.on_event("startup")
async def show_routes():
    print("\n=== Rotas registradas ===")
    for r in app.router.routes:
        methods = sorted(getattr(r, "methods", []))
        print(f"{methods} {r.path}")
    print("=========================\n")
