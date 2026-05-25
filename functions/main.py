# functions/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
from urllib.request import urlopen, Request
from collections import Counter

# 1) Carrega .env o mais cedo possível
load_dotenv()
print("Firebase cred path:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

# 2) Inicializa o Firebase uma única vez
from config.firebase_admin_init import init_firebase
init_firebase()

# 3) Cria a app UMA vez
app = FastAPI(title="PosGrad Board (Python + RTDB)")

# Habilita CORS para o frontend de desenvolvimento (Vite) e origens comuns
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RTDB_URL = os.getenv("RTDB_URL") or os.getenv("REACT_APP_RTDB_URL") or "https://poshbard-default-rtdb.firebaseio.com"

def _rtdb_get(path: str):
    """
    Acessa o Firebase RTDB e retorna os dados no caminho especificado.
    Usa a conexão autenticada do Firebase Admin SDK.
    """
    try:
        # Usar o SDK do Firebase que já foi inicializado
        from firebase_admin import db
        ref = db.reference(path)
        data = ref.get()
        return data or {}
    except Exception as e:
        import traceback
        print(f"Erro ao acessar RTDB ({path}): {str(e)}")
        traceback.print_exc()
        raise e

# 4) Endpoints básicos
@app.get("/", summary="Root")
def root():
    return {"status": "API rodando 🚀"}

@app.get("/health", summary="Health")
def health():
    return {"ok": True}

@app.get("/autores_flat", summary="RTDB proxy: autores_flat")
def autores_flat():
    try:
        data = _rtdb_get("autores_flat")
        return data or {}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RTDB error: {e}")

@app.get("/autores_flat/{author_id}", summary="RTDB proxy: autor (autores_flat/{id})")
def autores_flat_item(author_id: str):
    try:
        data = _rtdb_get(f"autores_flat/{author_id}")
        if data is None:
            raise HTTPException(status_code=404, detail="Autor não encontrado")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RTDB error: {e}")

@app.get("/autores/{author_id}/metrics", summary="Agrega métricas a partir de autores_flat.{id}.works")
def author_metrics(author_id: str):
    """
    Agrega métricas simples a partir do nó autores_flat/<id>/works:
    - publications_count, total_citations, h_index, first_year, last_year
    - top_concepts (lista [concept, count]) e top_coauthors (lista [name,count])
    - sample_publications (até 10 itens)
    """
    try:
        node = _rtdb_get(f"autores_flat/{author_id}")
        if not node:
            raise HTTPException(status_code=404, detail="Autor não encontrado")
        works = node.get("works") or node.get("work") or {}
        # normalize map -> list
        if isinstance(works, dict):
            items = [{**v, "id": k} for k, v in works.items() if k != "_"]
        elif isinstance(works, list):
            items = works
        else:
            items = []

        publications_count = len(items)
        citations_list = []
        years = []
        concepts_counter = Counter()
        coauthors_counter = Counter()
        sample = []

        for w in items:
            # citations
            cited = w.get("cited_by_count") or w.get("citations") or w.get("cited_by") or 0
            try:
                cited = int(cited)
            except Exception:
                cited = 0
            citations_list.append(cited)
            # year
            y = w.get("year") or w.get("ano") or w.get("published_year") or None
            try:
                if y is not None:
                    years.append(int(y))
            except Exception:
                pass
            # concepts
            for c in (w.get("concepts") or w.get("topics") or []):
                # c may be dict with 'display_name' or string
                if isinstance(c, dict):
                    name = c.get("display_name") or c.get("wikidata") or None
                    if name:
                        concepts_counter[name] += 1
                elif isinstance(c, str):
                    concepts_counter[c] += 1
            # coauthors (authorships or authors list)
            auths = w.get("authorships") or w.get("authors") or w.get("autores") or []
            if isinstance(auths, list):
                for a in auths:
                    if isinstance(a, dict):
                        n = a.get("author", {}).get("display_name") or a.get("name") or a.get("display_name")
                        if n:
                            coauthors_counter[n] += 1
                    elif isinstance(a, str):
                        coauthors_counter[a] += 1
            # sample
            if len(sample) < 10:
                sample.append({
                    "id": w.get("id") or w.get("work_id") or None,
                    "title": w.get("title") or w.get("titulo") or w.get("name") or "",
                    "year": w.get("year") or w.get("ano") or None,
                    "doi": w.get("doi") or w.get("DOI") or None,
                    "cited_by_count": cited
                })

        # total citations and h-index
        total_citations = sum(citations_list)
        sorted_cits = sorted(citations_list, reverse=True)
        h_index = 0
        for i, c in enumerate(sorted_cits, start=1):
            if c >= i:
                h_index = i
            else:
                break

        first_year = min(years) if years else None
        last_year = max(years) if years else None

        top_concepts = concepts_counter.most_common(10)
        top_coauthors = coauthors_counter.most_common(10)

        return {
            "author_id": author_id,
            "name": node.get("nome") or node.get("name") or node.get("display_name"),
            "publications_count": publications_count,
            "total_citations": total_citations,
            "h_index": h_index,
            "first_year": first_year,
            "last_year": last_year,
            "top_concepts": top_concepts,
            "top_coauthors": top_coauthors,
            "sample_publications": sample,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RTDB error: {e}")

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
