from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from functions.common.dbref import ref
from functions.repositories.produto_crud import ProdutoCRUD

router = APIRouter(tags=["Produtos"])

_crud: Optional[ProdutoCRUD] = None

def crud() -> ProdutoCRUD:
    global _crud
    if _crud is None:
        _crud = ProdutoCRUD()
    return _crud

@router.get("", summary="Listar")
@router.get("/", include_in_schema=False)
def listar(svc: ProdutoCRUD = Depends(crud)):
    return svc.list()


@router.get("/ranking", summary="Ranking de autores por número de produtos")
def ranking(svc: ProdutoCRUD = Depends(crud)):
    """
    Agrega produtos por autor (por nome) e retorna lista ordenada de {name, count}.
    O endpoint tenta lidar com campos `autores` em diferentes formatos (lista de strings,
    lista de objetos com campos name/author, ou string CSV).
    """
    # Tenta usar o nó RTDB 'autores' quando presente (mais confiável: vincula produto_id <-> docente_id)
    try:
        autores_node = ref("autores").get() or {}
        # contar por docente_id quando disponível
        counts_by_docente = {}
        for k, v in (autores_node or {}).items():
            if not isinstance(v, dict):
                continue
            docente_id = v.get("docente_id") or v.get("docenteId")
            if docente_id:
                counts_by_docente[docente_id] = counts_by_docente.get(docente_id, 0) + 1

        if counts_by_docente:
            # pegar nomes dos docentes para mapear
            docentes_node = ref("docentes").get() or {}
            out = []
            for did, cnt in counts_by_docente.items():
                name = None
                # procura em docetes node
                if isinstance(docentes_node, dict) and docentes_node.get(did):
                    d = docentes_node.get(did) or {}
                    name = d.get("nome") or d.get("name") or d.get("display_name")
                # fallback para usar o id como nome
                out.append({"name": name or str(did), "count": cnt})
            out.sort(key=lambda x: -x["count"]) 
            return out
    except Exception:
        # se algo falhar ao acessar RTDB diretamente, segue para fallback abaixo
        pass

    # Fallback: agregar por nome a partir do campo 'autores' dos produtos
    produtos = svc.list() or []
    counts = {}

    for p in produtos:
        autores_field = p.get("autores") or p.get("authorships") or p.get("autores_list") or p.get("authors")
        if not autores_field:
            continue
        # lista de objetos
        if isinstance(autores_field, list):
            for a in autores_field:
                name = None
                if isinstance(a, str):
                    name = a
                elif isinstance(a, dict):
                    name = a.get("name") or a.get("author_name") or (a.get("author") or {}).get("display_name")
                if not name:
                    continue
                n = str(name).strip()
                if not n:
                    continue
                counts[n] = counts.get(n, 0) + 1
        elif isinstance(autores_field, str):
            parts = [s.strip() for s in autores_field.split(",") if s.strip()]
            for name in parts:
                counts[name] = counts.get(name, 0) + 1

    arr = [{"name": k, "count": v} for k, v in counts.items()]
    arr.sort(key=lambda x: -x["count"]) 
    return arr
