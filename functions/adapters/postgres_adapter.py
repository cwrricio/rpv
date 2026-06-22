# functions/adapters/postgres_adapter.py
"""
Adaptador de armazenamento para PostgreSQL (SSQM — remoção do lock-in de dados).

Implementa o mesmo StoragePort do FirebaseRTDBAdapter usando SQLAlchemy, de modo
que trocar o backend (STORAGE_BACKEND=postgres) não exige reescrever os CRUDs.

Modelo de paridade com o RTDB no curto prazo: uma única tabela chave-valor
`kv_store(collection, id, data)`, onde `collection` é o antigo `path_root` e
`data` guarda o documento em JSON. Isso permite migrar nó a nó do Firebase sem
remodelar tudo de uma vez; a normalização relacional vem em fases posteriores.

A engine é parametrizável: SQLite em testes (portável, sem servidor) e
PostgreSQL em produção via docker-compose. O mesmo código roda nos dois.
"""
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    JSON,
    select,
    insert,
    update as sa_update,
    delete as sa_delete,
)

from functions.repositories.ports import StoragePort

_metadata = MetaData()

kv_store = Table(
    "kv_store",
    _metadata,
    Column("collection", String, primary_key=True),
    Column("id", String, primary_key=True),
    Column("data", JSON, nullable=False),
)


def _default_url() -> str:
    try:
        from config.settings import settings
        url = getattr(settings, "DATABASE_URL", None)
        if url:
            return url
    except Exception:
        pass
    return "postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard"


class PostgresAdapter(StoragePort):
    def __init__(self, url: Optional[str] = None):
        self._engine = create_engine(url or _default_url(), future=True)

    def init_schema(self) -> None:
        """Cria as tabelas se não existirem (idempotente)."""
        _metadata.create_all(self._engine)

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex

    def create(self, path_root: str, obj: Dict[str, Any]) -> Dict[str, Any]:
        new_id = self._new_id()
        with self._engine.begin() as conn:
            conn.execute(insert(kv_store).values(collection=path_root, id=new_id, data=obj))
        return {"id": new_id, **obj}

    def list(self, path_root: str) -> List[Dict[str, Any]]:
        stmt = select(kv_store.c.id, kv_store.c.data).where(kv_store.c.collection == path_root)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        out = []
        for row_id, data in rows:
            if isinstance(data, dict):
                out.append({"id": row_id, **data})
            else:
                out.append({"id": row_id, "value": data})
        return out

    def get(self, path_root: str, id: str) -> Optional[Dict[str, Any]]:
        stmt = select(kv_store.c.data).where(
            kv_store.c.collection == path_root, kv_store.c.id == id
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        if row is None:
            return None
        data = row[0]
        return {"id": id, **data} if isinstance(data, dict) else {"id": id, "value": data}

    def update(self, path_root: str, id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._engine.begin() as conn:
            row = conn.execute(
                select(kv_store.c.data).where(
                    kv_store.c.collection == path_root, kv_store.c.id == id
                )
            ).first()
            if row is None:
                return None
            current = row[0] if isinstance(row[0], dict) else {}
            merged = {**current, **patch}
            conn.execute(
                sa_update(kv_store)
                .where(kv_store.c.collection == path_root, kv_store.c.id == id)
                .values(data=merged)
            )
        return {"id": id, **merged}

    def delete(self, path_root: str, id: str) -> bool:
        with self._engine.begin() as conn:
            existing = conn.execute(
                select(kv_store.c.id).where(
                    kv_store.c.collection == path_root, kv_store.c.id == id
                )
            ).first()
            if existing is None:
                return False
            conn.execute(
                sa_delete(kv_store).where(
                    kv_store.c.collection == path_root, kv_store.c.id == id
                )
            )
        return True
