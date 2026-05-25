#!/usr/bin/env python3
import os
import time
from typing import Dict, Any

import firebase_admin
from firebase_admin import credentials, db


# ========= CONFIG POR AMBIENTE =========
PROJECT_ID = os.environ.get("PROJECT_ID", "poshbard")
RTDB_URL   = os.environ.get("RTDB_URL", "https://poshbard-default-rtdb.firebaseio.com")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

if not GOOGLE_CREDS or not os.path.exists(GOOGLE_CREDS):
    raise SystemExit("❌ Defina GOOGLE_APPLICATION_CREDENTIALS apontando para o service-account.json")

# ========= INIT FIREBASE ADMIN =========
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID, "databaseURL": RTDB_URL})


def ref(path: str):
    return db.reference(path)


def seed_base_nodes() -> None:
    """
    Cria nós base com placeholders para que 'pastas' apareçam no Console
    (RTDB não mantém nós vazios).
    """
    print("→ Criando nós base…")

    base_paths = [
        "instituicoes",
        "programas",
        "linhas",
        "docentes",
        "discentes",
        "projetos",
        "pesquisas",
        "veiculos",
        "produtos",
        "autores",

        # metamodelo operacional
        "staging/import_batches",
        "staging/orcid_bundles",
        "external_ids/doi",
        "external_ids/issn",
        "external_ids/openalex",
        "external_ids/openalex_author",
        "provenance",
    ]
    for p in base_paths:
        r = ref(p)
        cur = r.get()
        if cur is None:
            r.set({"_": True})   # placeholder visível
            print(f"  ✓ {p}/")


def seed_min_examples() -> Dict[str, Any]:
    """
    Insere exemplos mínimos nas tabelas de domínio para facilitar testes.
    Retorna os IDs criados/definidos.
    """
    print("→ Inserindo exemplos mínimos…")

    # Docentes/Discentes
    ref("docentes").update({
        "doc1": {"nome": "Prof A", "tipo": "PERMANENTE", "orcid": "0000-0001-6793-4033"},
        "doc2": {"nome": "Prof B", "tipo": "COLABORADOR"}
    })
    ref("discentes").update({
        "disc1": {"nome": "Aluno B", "status": "ATIVO"}
    })

    # Linha e Projeto
    ref("linhas").update({
        "linha1": {"titulo": "IA Aplicada", "descricao": "Aprendizado de Máquina"}
    })
    ref("projetos").update({
        "proj1": {"titulo": "Projeto X", "descricao": "Protótipo de ingestão/normalização", "dataInicio": "2025-01-10"}
    })

    # Pesquisa mínima (push key automática)
    pesq_ref = ref("pesquisas").push({
        "titulo": "Pesquisa RTDB de Exemplo",
        "projeto_id": "proj1",
        "linha_id": "linha1",
        "orientador_id": "doc1",
        "discente_id": "disc1",
        "status": "EM_ANDAMENTO",
        "coorientadores": {}
    })

    print("  ✓ doc1, doc2, disc1, linha1, proj1 e 1 pesquisa de exemplo criados.")
    return {"pesquisa_id": pesq_ref.key}


def seed_staging_orcid(orcid: str = "0000-0001-6793-4033") -> str:
    """
    Cria um bundle de staging 'ordenado por ORCID' para exercitar o fluxo:
      /staging/orcid_bundles/{orcid}/batches/{timestamp}
    Com 2 works fake (no formato que o processador por ORCID espera).
    """
    print(f"→ Criando staging ORCID bundle para {orcid} …")
    ts = str(int(time.time()))
    base = f"staging/orcid_bundles/{orcid}/batches/{ts}"

    author = {
        "id": f"https://openalex.org/A123456789",
        "display_name": "Prof A",
        "orcid": orcid,
        "works_count": 2,
        "cited_by_count": 10,
        "last_known_institutions": [],
        "topics": [],
        "works_api_url": "https://api.openalex.org/works?filter=author.id:A123456789"
    }
    works = {
        "WFAKE001": {
            "workId": "WFAKE001",
            "title": "Artigo de Exemplo 1",
            "type": "journal-article",
            "year": 2024,
            "doi": "10.1000/fake-doi-1",
            "url": "https://doi.org/10.1000/fake-doi-1",
            "venueId": "V123",
            "venue": "Revista Exemplo",
            "open_access": {"is_oa": True, "oa_status": "gold", "oa_url": "https://example.org/pdf1"},
            "cited_by_count": 5,
            "concepts": ["Machine Learning", "NLP"],
            "authorships": [
                {"author_id": "A123456789", "author_name": "Prof A", "raw_author_name": "A, Prof", "author_position": "first", "institutions": []}
            ]
        },
        "WFAKE002": {
            "workId": "WFAKE002",
            "title": "Artigo de Exemplo 2",
            "type": "proceedings-article",
            "year": 2025,
            "doi": "10.1000/fake-doi-2",
            "url": "https://doi.org/10.1000/fake-doi-2",
            "venueId": "V456",
            "venue": "Congresso Exemplo",
            "open_access": {"is_oa": False, "oa_status": "closed", "oa_url": None},
            "cited_by_count": 0,
            "concepts": ["Information Retrieval"],
            "authorships": [
                {"author_id": "A123456789", "author_name": "Prof A", "raw_author_name": "A, Prof", "author_position": "first", "institutions": []}
            ]
        }
    }

    ref(base).set({
        "author": author,
        "works": works,
        "updated_at": int(time.time())
    })
    print(f"  ✓ {base}/ com 2 works de exemplo.")
    return ts


def seed_external_ids_examples() -> None:
    """
    Exemplos em /external_ids (simula resoluções).
    """
    print("→ Inserindo exemplos de external_ids…")
    ref("external_ids/doi").update({
        "10.1000/fake-doi-1".replace("/", "_"): {"prodId": None},
        "10.1000/fake-doi-2".replace("/", "_"): {"prodId": None},
    })
    ref("external_ids/issn").update({
        "1234-5678": {"veicId": None}
    })
    print("  ✓ external_ids/doi e /issn preenchidos.")


def main():
    print("== SEED RTDB ==")
    seed_base_nodes()
    ids = seed_min_examples()
    seed_external_ids_examples()
    batch_ts = seed_staging_orcid(orcid="0000-0001-6793-4033")

    print("\nResumo:")
    print(f" - Pesquisa exemplo id: {ids['pesquisa_id']}")
    print(f" - Staging ORCID bundle: /staging/orcid_bundles/0000-0001-6793-4033/batches/{batch_ts}")
    print("\n✅ Concluído. Abra o Console do Firebase (Realtime DB) para visualizar os nós.")


if __name__ == "__main__":
    main()
