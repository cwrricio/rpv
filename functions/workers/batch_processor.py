# functions/workers/batch_processor.py
import time
from .openalex_mapper import map_work_to_prod
from .upsert import upsert_produto_bibliografico
from functions.common.dbref import ref

def _staging():
    return ref("staging/import_batches")

def process_batch(batch_id: str) -> dict:
    items = _staging().child(batch_id).child("items").get() or {}
    total = len(items)
    processed, errors = 0, 0

    for _, item in items.items():
        try:
            if item.get("source") != "OPENALEX":
                continue
            work = item.get("raw") or {}
            mapped = map_work_to_prod(work)
            upsert_produto_bibliografico(mapped)
            processed += 1
        except Exception:
            errors += 1

    _staging().child(batch_id).update({"processedAt": time.time(), "processed": processed, "errors": errors})
    return {"items": total, "processed": processed, "errors": errors}
