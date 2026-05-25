# functions/workers/openalex_mapper.py
def subtype_from_openalex_type(t: str) -> str:
    """
    Converte o 'type' do OpenAlex para seus subtipos internos de produção bibliográfica.
    Ajuste para seus enums (ex.: ARTIGO, CAPITULO, ANAIS, LIVRO).
    """
    t = (t or "").lower()
    if t in ("journal-article",):
        return "ARTIGO"
    if t in ("book-chapter",):
        return "CAPITULO"
    if t in ("proceedings-article", "conference-paper"):
        return "ANAIS"
    if t in ("book",):
        return "LIVRO"
    return "ARTIGO"

def map_work_to_prod(work: dict) -> dict:
    hv = work.get("host_venue") or {}
    issn = hv.get("issn_l")
    if not issn and isinstance(hv.get("issn"), list) and hv["issn"]:
        issn = hv["issn"][0]

    autores = []
    for i, a in enumerate(work.get("authorships", []), start=1):
        author = a.get("author") or {}
        orcid = author.get("orcid")
        autores.append({
            "papel": "AUTOR",
            "posicao": i,
            "contribuicao": None,
            # resolução posterior: tentamos casar ORCID com docentes/externos
            "externo_orcid": orcid
        })

    url = None
    pl = work.get("primary_location") or {}
    if isinstance(pl.get("source"), dict):
        url = pl["source"].get("url_for_landing_page")
    url = url or work.get("doi")

    return {
        "tipo": "BIBLIOGRAFICA",
        "subtipo": subtype_from_openalex_type(work.get("type")),
        "titulo": work.get("title"),
        "ano": work.get("publication_year"),
        "url": url,
        "doi": work.get("doi"),
        "issn": issn,
        "veiculo_nome": hv.get("display_name"),
        "autores": autores
    }
