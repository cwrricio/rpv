# Arquitetura — Poshboard

Objetivo: hospedar **front** e **back** de forma correta e preparar o backend em Python para **API** + **jobs agendados** (cron) para ingest/scraping (ex.: Lattes).

> Decisões arquiteturais formalizadas em `docs/adr/`. Consulte os ADRs antes de propor mudanças estruturais.

---

## Visão geral

- **Frontend:** React + Vite em `apresentacao/`, hospedado no Firebase Hosting.
- **Backend:** FastAPI em Python, entrypoint em `functions/main.py`.
- **Banco:** Firestore *(migração prevista — hoje ainda RTDB; ver ADR 0001)*.
- **Auth:** sem login real obrigatorio no estado atual; a estrategia alvo e OIDC
  provider-agnostic via porta `functions/auth/`, com `AUTH_PROVIDER=disabled`
  por padrao ate decisao de produto.
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

## Autenticacao provider-agnostic

Implementacao atual:

- `functions/auth/ports.py`: `AuthProviderPort` e `AuthenticatedUser`.
- `functions/auth/providers.py`: provider `disabled` e placeholder OIDC que
  falha fechado ate existir verificador JWT/JWKS aprovado.
- `functions/auth/dependencies.py`: dependencias FastAPI reutilizaveis para
  rotas futuras (`optional_user` e `required_user`).
- `functions/api_routes/auth.py`: diagnostico sem segredos em `/auth/config` e
  introspeccao em `/auth/me`.

Decisao: nao usar Firebase Auth como caminho canonico de login novo. Se login
real for necessario, a estrategia e OIDC independente de fornecedor, com
Keycloak self-hosted como opcao preferencial de soberania e alternativas
gerenciadas avaliadas por ADR.

Variaveis relevantes:

| Variavel | Descricao |
|---|---|
| `AUTH_PROVIDER` | `disabled` por padrao; `oidc` reservado para POC |
| `AUTH_REQUIRED` | `false` por padrao para nao bloquear rotas existentes |
| `OIDC_ISSUER_URL` | Issuer OIDC futuro |
| `OIDC_AUDIENCE` | Audience esperada pela API |
| `OIDC_JWKS_URL` | JWKS explicito, se o discovery nao for usado |

---

## Jobs/worker de ingestao (fila SQL)

Implementacao atual:

- `functions/jobs/ports.py`: `JobQueuePort`.
- `functions/jobs/sqlalchemy_queue.py`: fila portavel sobre SQLAlchemy (`job_queue`).
- `functions/jobs/worker.py`: worker dedicado (`python -m functions.jobs.worker`).
- `functions/api_routes/jobs.py`: consulta/listagem de jobs.

Fluxo:
1. A API recebe uma requisicao curta, por exemplo `POST /harvest/batch/jobs`.
2. A rota valida o payload e grava um job `harvest.batch` na fila.
3. O worker dedicado reserva o proximo job pronto, executa a ingestao pesada e
   grava resultado, retry ou dead-letter.
4. O usuario acompanha status por `GET /jobs/{job_id}` ou `GET /jobs?status=dead`.

O mecanismo usa o banco configurado em `DATABASE_URL`; em Docker, o servico
`worker` compartilha o PostgreSQL com o backend. Isso evita lock-in proprietario
e dispensa Redis/RabbitMQ nesta fase.

Variaveis relevantes:

| Variavel | Descricao |
|---|---|
| `DATABASE_URL` | Banco usado pela fila e pelo adaptador PostgreSQL |
| `STORAGE_BACKEND` | Deve ser `postgres` no Compose |
| `OPENALEX_MAILTO` | Identificacao educada para APIs academicas |

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
| `docs/adr/0006` | Autenticacao independente de provedor |
| `docs/relatorio-refatoracao.md` | Análise completa de refatoração |
