from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
import requests, time

from config.settings import settings

router = APIRouter(prefix="/ingest/orcid", tags=["ORCID"])

def _db():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db

def _ref(path: str):
    return _db().reference(path)

def _ua_headers() -> Dict[str, str]:
    mailto = (settings.OPENALEX_MAILTO or "").strip()
    ua = f"poshboard/0.1 ({'mailto:'+mailto if mailto else 'no-mailto'})"
    h = {"User-Agent": ua, "Accept": "application/json"}
    if mailto:
        h["From"] = mailto
    return h

def fetch_orcid_record(orcid: str) -> Dict[str, Any]:
    orcid = orcid.strip()
    url = f"https://pub.orcid.org/v3.0/{orcid}/record"
    r = requests.get(url, headers=_ua_headers(), timeout=25)
    if r.status_code == 404:
        raise HTTPException(404, f"ORCID {orcid} não encontrado")
    if not (200 <= r.status_code < 300):
        raise HTTPException(502, f"ORCID {r.status_code}: {r.text[:300]}")
    return r.json()

@router.get("/{orcid}", summary="Baixar profile ORCID e salvar em /external/orcid/{orcid}")
def get_and_save(orcid: str = Path(..., example="0000-0001-5457-2600")):
    data = fetch_orcid_record(orcid)
    ts = str(int(time.time()))
    base = _ref(f"external/orcid/{orcid}")
    base.child("record").set(data)
    base.child("batches").child(ts).set({"record": data, "imported_at": int(ts)})
    # campos úteis para consolidação
    name = (((data.get("person") or {}).get("name") or {}).get("display-name") or {}).get("value")
    emails = []
    for e in ((data.get("person") or {}).get("emails") or {}).get("email", []) or []:
        v = e.get("email")
        if v: emails.append(v)
    base.child("summary").update({"orcid": orcid, "display_name": name, "emails": emails, "last_import_ts": int(ts)})
    return {"ok": True, "orcid": orcid, "saved_to": f"/external/orcid/{orcid}"}
