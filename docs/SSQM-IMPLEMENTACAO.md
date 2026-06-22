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
  Hosting em favor de Docker e registra a decisão de project id único.

### Pessoa 4 — PostgreSQL + Docker (CLS-01, infraestrutura)
- `functions/adapters/postgres_adapter.py`: `StoragePort` em SQLAlchemy, tabela genérica
  `kv_store(collection, id, data)` para migração nó-a-nó.
- `config/settings.py`: `STORAGE_BACKEND` (default `firebase`) e `DATABASE_URL`; `PROJECT_ID`/
  `RTDB_URL` agora opcionais → a app sobe **sem Firebase** quando `STORAGE_BACKEND=postgres`.
- `Dockerfile.backend`, `apresentacao/Dockerfile` (+`nginx.conf`), `docker-compose.yml`
  (Postgres + backend + frontend), `.dockerignore`.

### Issue #7 — Migração RTDB → PostgreSQL (dados)
- `functions/repositories/ports.py`: `StoragePort` ganhou `upsert(path_root, id, obj)`
  para preservar ids legados em migracoes/backfills sem mudar o `create` usado pela API.
- `functions/adapters/firebase_adapter.py` e `functions/adapters/postgres_adapter.py`:
  implementam `upsert` e removem `id` embutido do payload para manter a chave canonica.
- `scripts/migrate_rtdb_to_postgres.py`: migra JSONs exportados por `scripts/export_rtdb.py`
  para PostgreSQL, com dry-run por padrao, `--apply`, validacao por item e manifesto de rollback.
- `functions/main.py`: leituras de `autores_flat` passaram pelo `StoragePort`, mantendo o
  formato historico `{id: payload}` e evitando acesso direto ao RTDB nessas consultas.

### Issue #8 — Project id Firebase unico (governanca)
- `poshbard` foi definido como project id Firebase legado canonico por estar alinhado
  com `.firebaserc` e com a RTDB URL usada pelos scripts legados.
- `.github/workflows/firebase-hosting-merge.yml` e
  `.github/workflows/firebase-hosting-pull-request.yml` deixam de apontar para
  `metaorganizer-project` e usam `FIREBASE_PROJECT_ID=poshbard`.
- O segredo project-specific antigo `FIREBASE_SERVICE_ACCOUNT_METAORGANIZER_PROJECT`
  foi substituido por `FIREBASE_SERVICE_ACCOUNT_POSHBARD` ou pelo segredo generico
  `FIREBASE_SERVICE_ACCOUNT`.
- `scripts/seed_rtdb.py` passou a derivar a `RTDB_URL` padrao do project id ativo,
  reduzindo duplicacao de constantes Firebase.

### Issue #12 — Jobs/worker para ingestao pesada (CLS-06)
- `functions/jobs/ports.py`: nova porta `JobQueuePort`, separando a API HTTP do
  mecanismo concreto de fila.
- `functions/jobs/sqlalchemy_queue.py`: fila portavel em SQLAlchemy (`job_queue`),
  com idempotencia, retries, backoff simples e dead-letter (`status=dead`).
- `functions/jobs/worker.py`: worker dedicado executavel por
  `python -m functions.jobs.worker`, com logs basicos por job.
- `functions/api_routes/harvest_authors.py`: novo endpoint assíncrono
  `POST /harvest/batch/jobs`, preservando `POST /harvest/batch` como rota
  síncrona legada para compatibilidade.
- `functions/api_routes/jobs.py`: observabilidade basica para consultar/listar jobs.
- `docker-compose.yml`: novo servico `worker`, usando a mesma imagem do backend e
  o mesmo PostgreSQL.
- Limitacoes atuais: replay de dead-letter ainda e manual e nao ha reaper automatico
  para jobs que fiquem presos em `running` se o processo morrer no meio da execucao.

### Issue #14 — Estrategia de autenticacao propria (DEP-03)
- Estado atual validado: o frontend possui tela/contexto de login, mas sem login
  real; `firebaseClient.js` esta stubado e o backend nao verifica JWT em rotas.
- `functions/auth/ports.py`: nova porta `AuthProviderPort` e identidade
  normalizada `AuthenticatedUser`, sem dependencia de Firebase.
- `functions/auth/providers.py`: provider `disabled` como padrao seguro e
  placeholder OIDC que falha fechado ate existir verificador JWT/JWKS aprovado.
- `functions/auth/dependencies.py`: dependencias FastAPI reutilizaveis para
  proteger rotas futuras sem espalhar detalhes do provedor.
- `functions/api_routes/auth.py`: endpoints de POC/diagnostico
  `GET /auth/config` e `GET /auth/me`.
- `docs/adr/0006-autenticacao-oidc-independente.md`: ADR comparando manter sem
  auth real, Firebase Auth, Keycloak/OIDC self-hosted e provedores gerenciados.
- Limitacoes atuais: nenhuma rota de negocio foi protegida, `AUTH_REQUIRED`
  continua `false` por padrao e a validacao real OIDC depende de decisao de
  produto e escolha de biblioteca/verificador JWT.

## TDD / Testes

Test-first nas frentes com lógica pura:
- `tests/test_postgres_adapter.py` (contrato sobre SQLite).
- `tests/test_export_rtdb.py` (3 testes).
- `tests/test_storage_contract.py` (paridade do `StoragePort`, incluindo `upsert`).
- `tests/test_migrate_rtdb_to_postgres.py` (migracao, validacao e rollback sobre SQLite).
- `tests/test_firebase_project_governance.py` (drift de project id Firebase legado).
- `tests/test_job_queue.py` (fila, retries/dead-letter e execucao do worker).
- `tests/test_auth_strategy.py` (porta de auth, provider disabled e OIDC fail-closed).
- `tests/test_base_crud.py` adaptado para injeção de `StoragePort`.

**Resultado anterior:** `65 passed, 1 skipped` (o skip é o teste opt-in contra o emulador Firebase real).
**Verificacao issue #7:** testes focados de adaptador/contrato/migracao passam em SQLite.
**Verificacao issue #12:** testes focados de fila/worker passam em SQLite.
**Verificacao issue #14:** testes focados de estrategia de auth passam sem Firebase.

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

# Migracao RTDB JSON -> PostgreSQL (dry-run por padrao)
python scripts/migrate_rtdb_to_postgres.py --source exports/<timestamp>

# Aplicar e gerar manifesto de rollback
python scripts/migrate_rtdb_to_postgres.py --source exports/<timestamp> --apply

# Rollback manual a partir do manifesto gerado
python scripts/migrate_rtdb_to_postgres.py --rollback exports/<timestamp>/migration_rollback_<timestamp>.json

# Worker de ingestao em Docker
docker compose up --build worker

# Worker local
python -m functions.jobs.worker --once
```

## Próximos passos (issues)

Ver `scripts/github_issues.sh` — uma issue por frente + dívidas remanescentes de migração
(principalmente queries RTDB ainda legadas).
