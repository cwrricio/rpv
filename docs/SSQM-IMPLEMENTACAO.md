# Relatório de Implementação SSQM — Parte 1 (branch `SSQM`)

**Data:** 2026-06-21
**Base:** `relatorio-final-ssqm.md` (Roadmap Curto Prazo) + antecipação do adaptador PostgreSQL.
**Diretriz do usuário:** Docker em tudo; **a forma de obter dados de trabalhos (ingestão via
APIs externas) NÃO muda**; TDD; tudo na branch `SSQM`.

## Objetivo

Reduzir o lock-in de dados/operação em Firebase/Google (SSQMScore inicial 43,3%, Nível 3)
**antes** de trocar a infraestrutura, criando portas/adaptadores, removendo acessos diretos
e tornando o deploy portável via Docker.

## Divisão em 4 frentes (pessoas)

| Frente | Tema | Status |
|---|---|---|
| Pessoa 1 | Camada de portas/adaptadores (Soberania Arquitetural) | ✅ implementada |
| Pessoa 2 | Frontend só-API (remover RTDB direto) | ✅ implementada |
| Pessoa 3 | Export de dados + drift de config + modelo de dados | ✅ implementada |
| Pessoa 4 | Adaptador PostgreSQL + Docker + testes (TDD) | ✅ implementada |

## O que foi feito

### Pessoa 1 — Portas/Adaptadores (CLS-01, CLS-02)
- `functions/repositories/ports.py`: `StoragePort` (contrato `create/list/get/update/delete`).
- `functions/adapters/firebase_adapter.py`: `FirebaseRTDBAdapter` encapsula toda a API RTDB.
- `functions/adapters/__init__.py`: factory `get_storage()` (default `firebase`, gancho `postgres`).
- `functions/repositories/base.py`: `BaseCRUD` delega ao `StoragePort` injetado.
- Removido `firebase_admin.db` direto de `functions/services/pesquisa.py` e `functions/main.py`
  (roteados por `functions/common/dbref.ref`).
- Escape hatch `ref()`/`raw_ref()` mantém as queries RTDB ainda não portadas
  (`DocenteCRUD.find_by_orcid`, `PesquisaService.listar`) — listadas como dívida em `DATA_MODEL.md`.

### Pessoa 2 — Frontend só-API (CLS-03, CLS-09)
- Removidos `RTDB_FALLBACK`/`VITE_RTDB_URL` e todos os fetches `*.firebaseio.com/*.json` de
  `Home.jsx`, `Home/Home.jsx`, `RelatorioProducao.jsx`, `Qualis/Qualis.jsx`.
- Frontend consome **somente** a API FastAPI.
- Removida a dependência `firebase` de `apresentacao/package.json` (cliente já era stub).
- Verificação: `grep -rn "firebaseio|VITE_RTDB" apresentacao/src` → 0 ocorrências.

### Pessoa 3 — Soberania de dados e governança (CLS-07, exportação)
- `scripts/export_rtdb.py`: exporta cada nó para `exports/<timestamp>/<no>.{json,csv}`.
- `docs/DATA_MODEL.md`: mapa de coleções canônicas + dívidas de migração.
- `docs/ADR-001-config-drift.md`: corrige hosting dir (`apresentacao/dist`), depreca Firebase
  Hosting em favor de Docker e registra a decisão pendente sobre o project id único.

### Pessoa 4 — PostgreSQL + Docker (CLS-01, infraestrutura)
- `functions/adapters/postgres_adapter.py`: `StoragePort` em SQLAlchemy, tabela genérica
  `kv_store(collection, id, data)` para migração nó-a-nó.
- `config/settings.py`: `STORAGE_BACKEND` (default `firebase`) e `DATABASE_URL`; `PROJECT_ID`/
  `RTDB_URL` agora opcionais → a app sobe **sem Firebase** quando `STORAGE_BACKEND=postgres`.
- `Dockerfile.backend`, `apresentacao/Dockerfile` (+`nginx.conf`), `docker-compose.yml`
  (Postgres + backend + frontend), `.dockerignore`.

## TDD / Testes

Test-first nas frentes com lógica pura:
- `tests/test_postgres_adapter.py` (8 testes, contrato sobre SQLite).
- `tests/test_export_rtdb.py` (3 testes).
- `tests/test_base_crud.py` adaptado para injeção de `StoragePort`.

**Resultado:** `65 passed, 1 skipped` (o skip é o teste opt-in contra o emulador Firebase real).

## O que NÃO mudou (por requisito)

- `functions/ingest/*` e a coleta de dados de trabalhos via OpenAlex/ORCID/Crossref/Semantic
  Scholar permanecem intactos.

## Como rodar

```bash
# Stack completo em Docker (Postgres + API + frontend)
docker compose up --build
# frontend: http://localhost:8080   API: http://localhost:8000

# Testes
python -m pytest -q

# Export de emergência dos dados (requer credenciais Firebase)
python scripts/export_rtdb.py
```

## Próximos passos (issues)

Ver `scripts/github_issues.sh` — uma issue por frente + dívidas de migração (queries RTDB),
project id único e migração de dados RTDB→Postgres.
