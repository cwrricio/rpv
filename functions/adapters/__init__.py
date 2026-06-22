# functions/adapters/__init__.py
"""
Factory de armazenamento (porta -> adaptador concreto).

Seleciona o adaptador ativo via `STORAGE_BACKEND` (config/settings.py).
Default: "firebase" — comportamento idêntico ao legado. O gancho "postgres"
fica reservado para a fatia da Pessoa 4 (adaptador PostgreSQL).
"""
from functions.repositories.ports import StoragePort

_INSTANCE: StoragePort | None = None


def get_storage() -> StoragePort:
    """Retorna o adaptador de armazenamento ativo (singleton)."""
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE

    backend = "firebase"
    try:
        from config.settings import settings
        backend = (getattr(settings, "STORAGE_BACKEND", None) or "firebase").lower()
    except Exception:
        backend = "firebase"

    if backend == "postgres":
        # Reservado para a Pessoa 4. Enquanto não existir, falha de forma clara.
        try:
            from functions.adapters.postgres_adapter import PostgresAdapter
            adapter = PostgresAdapter()
            adapter.init_schema()
            _INSTANCE = adapter
            return _INSTANCE
        except ImportError as e:
            raise RuntimeError(
                "STORAGE_BACKEND=postgres mas o PostgresAdapter ainda não está disponível."
            ) from e

    from functions.adapters.firebase_adapter import FirebaseRTDBAdapter
    _INSTANCE = FirebaseRTDBAdapter()
    return _INSTANCE
