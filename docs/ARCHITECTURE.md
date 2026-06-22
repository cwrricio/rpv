# Arquitetura — Poshboard

**Última atualização**: 2026-06-22  
**Status**: Implementado (Ports/Adapters com PostgreSQL + Firebase)

> Decisões arquiteturais formalizadas em `docs/adr/`. Consulte os ADRs antes de propor mudanças estruturais.

---

## Visão Geral

- **Frontend**: React + Vite em `apresentacao/`, servido via nginx (Docker) ou Firebase Hosting (legado)
- **Backend**: FastAPI em Python, entrypoint em `functions/main.py`
- **Banco**: PostgreSQL (via StoragePort) ou Firebase Realtime Database (legado)
- **Arquitetura**: **Ports/Adapters** — camada de domínio isolada, adaptadores para infra
- **Cache**: Metadados acadêmicos em cache local com fallback para APIs externas
- **Jobs**: Cloud Run Jobs + Cloud Scheduler para ingestão/scraping

---

## Hospedagem

| Componente | Serviço | Motivo |
|---|---|---|
| Frontend | Firebase Hosting | Deploy estático simples via `firebase deploy` |
| Backend API | Cloud Run (container Uvicorn) | FastAPI exige processo contínuo — incompatível com Firebase Functions (ver ADR 0003) |
| Jobs/cron | Cloud Run Jobs + Cloud Scheduler | Execução agendada fora do HTTP |

---

## Estrutura de Pastas

```
functions/
├── main.py              # entrypoint FastAPI: middleware, registro de routers
├── api_routes/          # [Interface HTTP] handlers de rota; sem lógica de negócio
├── workers/             # [Aplicação] processamento em lote e jobs agendados
├── services/            # [Aplicação] orquestração e lógica de negócio
├── domain/              # [Domínio] tipos, enums e regras
├── repositories/        # [Porta] StoragePort (protocolo)
├── adapters/            # [Infra] Adaptadores: FirebaseRTDBAdapter, PostgresAdapter
├── ingest/              # [Infra] APIs externas (OpenAlex, ORCID, Crossref, S2)
└── common/              # [Infra] utils (dbref, http_client, metadata_cache)
```

> **Nota de nomenclatura**: a pasta `crud/` foi renomeada para `repositories/`. Ver ADR 0002.

---

## Camadas e regra de dependência

```
[Interface]     api_routes/ + jobs/
                      ↓
[Aplicação]     services/ + workers/
                      ↓
[Domínio]       domain/
                      ↓
[Infra]         repositories/ + ingest/ + config/
```

**Regra:** cada camada só conhece a camada imediatamente abaixo. `api_routes` chama `services`, que chama `repositories` ou `ingest`. `api_routes` **nunca** acessa o banco diretamente.

---

## Modelo de dados: Raw e Canonical

O sistema armazena dados externos em duas camadas (ver ADR 0004):

- **Raw:** dado exatamente como veio da API externa. Salvo em `/openalex/{id}/batches/`, `/external/{fonte}/{id}/`. Nunca alterado. Nunca lido pela interface.
- **Canonical:** dado normalizado e unificado, pronto para consumo. Salvo em `/autores_flat/{slug}`, `/produtos/{id}`, etc.

O pipeline é: `ingest/` coleta e salva raw → `workers/` processa e grava canonical → `api_routes/` serve canonical.

---

## Deploy do backend (Cloud Run)

```bash
# build e push da imagem
docker build -t poshboard-api .
docker push gcr.io/<PROJECT_ID>/poshboard-api

# execução no container
uvicorn functions.main:app --host 0.0.0.0 --port $PORT
```

**Credenciais:**
- Cloud Run: Service Account vinculada ao serviço via ADC. Nenhum JSON no container.
- Local: `GOOGLE_APPLICATION_CREDENTIALS` apontando para o arquivo JSON de service account.

**Variáveis de ambiente obrigatórias:**

| Variável | Descrição |
|---|---|
| `PROJECT_ID` | ID do projeto Firebase/GCP |
| `RTDB_URL` | URL do Realtime Database *(temporário — removido após ADR 0001)* |
| `CORS_ORIGINS` | Origens permitidas separadas por vírgula (ex.: `https://poshboard.web.app`) |
| `OPENALEX_MAILTO` | E-mail para o polite pool da API OpenAlex (opcional, mas recomendado) |

> `CORS_ORIGINS` deve ser configurado no Cloud Run. Nunca hardcoded no código.

---

## Jobs agendados (Cloud Run Job + Cloud Scheduler)

Job implementado: `functions/jobs/harvest_docentes.py`

Fluxo:
1. Lê `docentes` do banco.
2. Para cada docente com `nome` (e opcionalmente `orcid`), coleta dados do OpenAlex.
3. Salva raw via `ingest/`.
4. Processa canonical via `workers/`.

Variáveis de ambiente do job:

| Variável | Descrição |
|---|---|
| `HARVEST_LIMIT` | Número máximo de docentes por execução |
| `HARVEST_MAX_WORKS_PAGES` | Páginas máximas de obras por autor |
| `HARVEST_SLEEP_S` | Intervalo entre requisições (rate limit) |

Próximo adapter: `functions/ingest/lattes/` para coleta via Currículo Lattes.

---

## Handlers síncronos (dívida técnica conhecida)

Todos os handlers são `def` síncronos, não `async def`. O FastAPI os executa em thread pool interno — correto, mas não ideal (ver ADR 0005).

**Gatilho de resolução:** quando a migração para Firestore (ADR 0001) for executada, todos os handlers devem ser convertidos para `async def` usando o `AsyncClient` do Firestore.

---

## Diagramas

O projeto tem o gerador `uml_packages.py`:

```bash
python uml_packages.py --root . --max-depth 4 --min-files 1
```

Gera:
- `packages.puml` — pacotes e pastas
- `components.puml` — componentes e dependências por imports

---

## Referências

| Documento | Conteúdo |
|---|---|
| `CONTEXT.md` | Glossário de domínio |
| `docs/adr/0001` | Firestore em vez de RTDB |
| `docs/adr/0002` | Manutenção sem reengenharia |
| `docs/adr/0003` | Cloud Run em vez de Firebase Functions |
| `docs/adr/0004` | Modelo Raw e Canonical |
| `docs/adr/0005` | Handlers síncronos como dívida técnica |
| `docs/relatorio-refatoracao.md` | Análise completa de refatoração |
