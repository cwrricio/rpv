# functions/crud/validators.py
import re

ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dxX]$")
DOI_RE  = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

def validate_issn(issn: str | None) -> bool:
    if not issn:
        return True
    return bool(ISSN_RE.match(issn))

def validate_doi(doi: str | None) -> bool:
    if not doi:
        return True
    return bool(DOI_RE.match(doi))

def normalize_doi_url(doi: str | None) -> str | None:
    if not doi:
        return None
    if doi.startswith("http"):
        return doi
    return f"https://doi.org/{doi.replace('doi:', '')}"
