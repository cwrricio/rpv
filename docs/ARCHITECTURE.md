# Arquitetura — Poshboard

Objetivo: hospedar **front** e **back** de forma correta e preparar o backend em Python para **API** + **jobs agendados** (cron) para ingest/scraping (ex.: Lattes).

> Decisões arquiteturais formalizadas em `docs/adr/`. Consulte os ADRs antes de propor mudanças estruturais.

---

## Visão geral

- **Frontend:** React + Vite em `apresentacao/`, hospedado no Firebase Hosting.
- **Backend:** FastAPI em Python, entrypoint em `functions/main.py`.
- **Banco:** Firestore *(migração prevista — hoje ainda RTDB; ver ADR 0001)*.
- **Auth:** Firebase Authentication no frontend; backend verifica o ID Token (JWT) nas rotas protegidas.
- **Jobs/cron:** Cloud Run Jobs disparados pelo Cloud Scheduler, lendo e gravando no banco.

---

## Hospedagem

| Componente | Serviço | Motivo |
|---|---|---|
| Frontend | Firebase Hosting | Deploy estático simples via `firebase deploy` |
| Backend API | Cloud Run (container Uvicorn) | FastAPI exige processo contínuo — incompatível com Firebase Functions (ver ADR 0003) |
| Jobs/cron | Cloud Run Jobs + Cloud Scheduler | Execução agendada fora do HTTP |

---

## Estrutura de pastas

```
functions/
├── main.py              ← entrypoint FastAPI: middleware, registro de routers
├── api_routes/          ← [Interface HTTP] handlers de rota; sem lógica de negócio
├── jobs/                ← [Interface Cron] entrypoints executáveis via Cloud Run Job
├── services/            ← [Aplicação] orquestração e lógica de negócio
├── workers/             ← [Aplicação] processamento em lote (ex.: pipeline raw→canonical)
├── domain/              ← [Domínio] tipos, enums e regras (TipoDocente, StatusPesquisa)
├── repositories/        ← [Infraestrutura] acesso ao banco (Firestore/RTDB); BaseCRUD aqui
├── ingest/              ← [Infraestrutura] clientes HTTP externos (OpenAlex, ORCID, Crossref, S2)
└── common/              ← utilitários compartilhados (ex.: dbref.py — único ponto de init do banco)

config/
├── firebase_admin_init.py   ← inicialização única do Firebase Admin SDK
└── settings.py              ← variáveis de ambiente centralizadas
```

> **Nota de nomenclatura:** a pasta era `crud/` (renomeada para `repositories/`) e `commom/` com typo (corrigida para `common/`). Ver ADR 0002.

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
