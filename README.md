# Poshboard

Dashboard para programas de pós-graduação.

O projeto tem duas partes:

- **Backend**: API em Python (FastAPI). A persistência passa por uma camada de
  **portas/adaptadores** (`functions/repositories/ports.py` → `StoragePort`),
  com dois adaptadores selecionáveis por `STORAGE_BACKEND`:
  - `firebase` (default/legado): Firebase Realtime Database via Admin SDK.
  - `postgres`: PostgreSQL via SQLAlchemy — **roda sem qualquer dependência Google**.
- **Frontend**: app React (Vite) em `apresentacao/`, que consome **somente a API** (sem acesso direto ao banco).

> 📄 Contexto e detalhes da migração de soberania: `docs/SSQM-IMPLEMENTACAO.md`,
> `docs/DATA_MODEL.md` e `docs/ADR-001-config-drift.md`.

## Requisitos

- Python 3.11+ (testado localmente com 3.12)
- Node.js 20+ 
- Docker + Docker Compose (recomendado para subir o stack completo)
- Credenciais do Firebase **apenas** se usar `STORAGE_BACKEND=firebase` (ver seção **Credenciais**)

## Setup rápido (local)

### 1) Backend (FastAPI)

> As instruções abaixo usam **bash** (Linux/macOS). No Windows, veja a subseção **Windows** (PowerShell/CMD) ou use os scripts em `scripts/windows/` para rodar de forma mais automática.

#### Linux/macOS (bash)

1. Crie/ative um virtualenv e instale dependências:

	```bash
	python -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt
	```

#### Windows (PowerShell)

1. Crie o virtualenv e instale dependências (sem depender de `pip` global):

	```powershell
	# se o comando `py` não existir, use `python` no lugar
	py -m venv venv
	.\venv\Scripts\python.exe -m pip install -r requirements.txt
	```

2. (Opcional) Ative o virtualenv na sessão atual (útil para rodar `pytest`, etc.):

	```powershell
	# se sua máquina bloquear scripts, rode antes:
	# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
	.\venv\Scripts\Activate.ps1
	```

#### Windows (CMD)

1. Crie o virtualenv e instale dependências:

	```bat
	REM se o comando `py` não existir, use `python` no lugar
	py -m venv venv
	venv\Scripts\python -m pip install -r requirements.txt
	```

2. (Opcional) Ative o virtualenv na sessão atual:

	```bat
	venv\Scripts\activate.bat
	```

#### Windows (automatizado)

Se você quiser evitar a etapa de ativação do virtualenv, rode o backend via script (ele cria o venv se necessário, instala dependências e inicia o Uvicorn):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\backend.ps1 -Port 8000
```

2. Configure variáveis de ambiente criando/ajustando um arquivo `.env` na raiz.

	Variáveis usadas pelo backend (ver `config/settings.py`):

	- `STORAGE_BACKEND` (opcional, padrão `firebase`) — `firebase` ou `postgres`.
	- `DATABASE_URL` (obrigatório se `STORAGE_BACKEND=postgres`) — ex.: `postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard`
	- `PROJECT_ID` (obrigatório se `STORAGE_BACKEND=firebase`) — project id canônico legado: `poshbard`
	- `FIREBASE_PROJECT_ID` (opcional; usado por scripts/workflows legados) — default: `poshbard`
	- `RTDB_URL` (obrigatório se `STORAGE_BACKEND=firebase`) — ex.: `https://<seu-projeto>-default-rtdb.firebaseio.com`
	- `API_PORT` (opcional, padrão `8000`)
	- `OPENALEX_MAILTO` (opcional)
	- `GOOGLE_APPLICATION_CREDENTIALS` (opcional; ver **Credenciais**)
	- `AUTH_PROVIDER` (opcional, padrao `disabled`) — `disabled` ou `oidc`.
	- `AUTH_REQUIRED` (opcional, padrao `false`) — nao proteja rotas ate haver decisao de produto.
	- `OIDC_ISSUER_URL`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL` (opcionais; reservados para POC OIDC).

	Dica: existe um `.env.example` para referência.

3. Suba a API:

	```bash
	uvicorn functions.main:app --reload --host 127.0.0.1 --port ${API_PORT:-8000}
	```

	No Windows (PowerShell/CMD), prefira informar a porta diretamente:

	```powershell
	uvicorn functions.main:app --reload --host 127.0.0.1 --port 8000
	```

4. Verifique:

	- http://127.0.0.1:8000/health
	- http://127.0.0.1:8000/docs (Swagger)

### 2) Frontend (Vite/React)

1. Instale dependências:

	```bash
	cd apresentacao
	npm ci
	```

2. (Opcional) Configure variáveis de ambiente do Vite criando `apresentacao/.env`:

	- `VITE_API_URL` (padrão: `http://127.0.0.1:8000`) — o frontend consome somente a API.

	> O antigo `VITE_RTDB_URL` (leitura direta do RTDB) foi **removido** na migração SSQM.

3. Rode o dev server:

	```bash
	npm run dev
	```

	Windows (automatizado):

	```powershell
	powershell -ExecutionPolicy Bypass -File .\scripts\windows\frontend.ps1
	```

4. Abra:

	- http://localhost:5173

## Credenciais (Firebase Admin SDK)

O backend inicializa o Firebase usando **Application Default Credentials** (`credentials.ApplicationDefault()`).

Opções comuns em desenvolvimento local:

- **Service account JSON**: defina `GOOGLE_APPLICATION_CREDENTIALS` apontando para um arquivo JSON.
  Exemplo:

  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
  ```

- **gcloud ADC** (se você usa Google Cloud SDK):

  ```bash
  gcloud auth application-default login
  ```

Importante:

- Trate JSON de service account como **segredo**. Não commite e não embuta em imagens Docker.


## Variáveis de Ambiente — CORS

A lista de origens permitidas pelo backend é configurada via variável de ambiente:

| Variável | Obrigatório | Exemplo | Descrição |
|---|---|---|---|
| `CORS_ORIGINS` | Não | `http://localhost:5173,https://meu-app.web.app` | Origens CORS separadas por vírgula |

Se `CORS_ORIGINS` não for definida, o backend aceita apenas as origens locais de desenvolvimento (`localhost:5173`, `localhost:3000`, `localhost:8000`).

**Exemplo no `.env`:**
```
CORS_ORIGINS=http://localhost:5173,https://meu-projeto.web.app,https://meu-dominio.com
```

> ⚠️ Em produção, defina `CORS_ORIGINS` explicitamente com apenas as origens autorizadas — nunca use `*` com `allow_credentials=True`.

## Autenticacao

O estado atual do produto continua sem login real obrigatorio. A API ganhou uma
porta de autenticacao independente de provedor em `functions/auth/`, mas o
provedor padrao e `AUTH_PROVIDER=disabled`, para manter o sistema executavel e
nao reintroduzir dependencia de Firebase Auth ou identidade Google.

Endpoints de diagnostico:

```bash
curl http://127.0.0.1:8000/auth/config
curl http://127.0.0.1:8000/auth/me
```

Se o produto aprovar login real, o caminho recomendado e OIDC provider-agnostic
(por exemplo Keycloak self-hosted). A POC ainda precisa adicionar verificacao
JWT/JWKS antes de proteger rotas com `AUTH_REQUIRED=true`; ate la, `oidc` falha
fechado para tokens recebidos.

## Testes (backend)

A suíte de testes do backend vive em `tests/` e usa `pytest`.

1. Instale as dependências de desenvolvimento (inclui `pytest` e `httpx`):

	```bash
	pip install -r requirements-dev.txt
	```

2. Rode a suíte a partir da raiz do projeto:

	```bash
	pytest
	```

Os testes unitários e de rota **não** acessam o Firebase (usam stubs/fakes em
memória), então rodam sem credenciais nem rede. O teste de integração de
`BaseCRUD` contra o **emulador Firebase** é pulado por padrão; para executá-lo:

```bash
firebase emulators:start --only database
# em outro terminal, com a porta do emulador exposta pelo CLI:
FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000 pytest tests/test_base_crud.py
```

No Windows:

- PowerShell:

	```powershell
	$env:FIREBASE_DATABASE_EMULATOR_HOST = "127.0.0.1:9000"
	pytest tests\test_base_crud.py
	```

- CMD:

	```bat
	set FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000 && pytest tests\test_base_crud.py
	```

## Migrar RTDB JSON para PostgreSQL

Use primeiro `scripts/export_rtdb.py` para gerar `exports/<timestamp>/<colecao>.json`.
O migrador nao acessa Firebase: ele usa esses JSONs como fonte e escreve no
PostgreSQL via `StoragePort`/`PostgresAdapter`.

```bash
# Dry-run: valida os arquivos e mostra o plano, sem escrever no banco
python scripts/migrate_rtdb_to_postgres.py --source exports/<timestamp>

# Aplicar no PostgreSQL preservando ids do RTDB
python scripts/migrate_rtdb_to_postgres.py \
  --source exports/<timestamp> \
  --database-url postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard \
  --apply

# Opcional: espelhar exatamente o export removendo ids extras da colecao alvo
python scripts/migrate_rtdb_to_postgres.py --source exports/<timestamp> --apply --replace

# Rollback usando o manifesto criado na aplicacao
python scripts/migrate_rtdb_to_postgres.py \
  --database-url postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard \
  --rollback exports/<timestamp>/migration_rollback_<timestamp>.json
```

## Jobs de ingestao academica

A ingestao pesada pode ser enfileirada para um worker dedicado, sem lock-in
proprietario: a fila usa SQLAlchemy sobre o mesmo `DATABASE_URL` do backend
(`job_queue` no PostgreSQL; SQLite nos testes).

```bash
# Enfileirar harvest em lote (retorna 202 + job_id)
curl -X POST http://127.0.0.1:8000/harvest/batch/jobs \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: harvest-2026-06-22-demo" \
  -d '{"items":[{"name":"Diego Luis Kreutz"}],"max_works_pages":1}'

# Consultar observabilidade basica
curl http://127.0.0.1:8000/jobs/<job_id>
curl "http://127.0.0.1:8000/jobs?status=dead"

# Rodar worker local fora do Docker
python -m functions.jobs.worker --poll-interval 2
python -m functions.jobs.worker --once
```

Retries sao automaticos ate `max_attempts` (default: 3). Jobs que excedem as
tentativas ficam com `status=dead` para inspeção/manual replay posterior.

## Rodar com Docker (recomendado)

O `docker-compose.yml` sobe o stack completo — **PostgreSQL + backend + worker + frontend** —
sem depender de Firebase (`STORAGE_BACKEND=postgres` por padrão no compose):

```bash
docker compose up --build
```

Depois acesse:

- Frontend: http://localhost:8080
- API: http://localhost:8000/health  •  Swagger: http://localhost:8000/docs
- Worker: servico `worker` no Compose, sem porta HTTP; acompanhe por `docker compose logs -f worker`

Imagens individuais: `Dockerfile.backend` (FastAPI/Uvicorn) e `apresentacao/Dockerfile`
(build Vite servido por nginx, com proxy `/api` → backend).

## Firebase Hosting / Emulator (legado, em depreciação)

> A publicação canônica passou a ser via Docker (ver acima). O Firebase Hosting é
> mantido como legado; ver `docs/ADR-001-config-drift.md`.

O hosting está configurado para publicar `apresentacao/dist` (ver `firebase.json`).

- Build do frontend: `npm --prefix apresentacao run build`
- Emulator de hosting: `firebase emulators:start`
- Project id Firebase legado canonico: `poshbard`.
- Workflows de Hosting usam `FIREBASE_PROJECT_ID=poshbard` e esperam o segredo
  `FIREBASE_SERVICE_ACCOUNT_POSHBARD` ou `FIREBASE_SERVICE_ACCOUNT`.
- O segredo antigo `FIREBASE_SERVICE_ACCOUNT_METAORGANIZER_PROJECT` ficou obsoleto.

## Troubleshooting

- **Erro do Pydantic dizendo que `PROJECT_ID`/`RTDB_URL` não foram informados**: confira seu `.env` na raiz.
- **`DefaultCredentialsError` / problema de credenciais**: ajuste `GOOGLE_APPLICATION_CREDENTIALS` ou faça `gcloud auth application-default login`.
- **Frontend não consegue chamar a API**: confirme `VITE_API_URL` e se a API está em `127.0.0.1:8000` (CORS já permite `localhost:5173`).
