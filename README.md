# Poshboard

Dashboard para programas de pós-graduação.

O projeto tem duas partes:

- **Backend**: API em Python (FastAPI) que lê/escreve no Firebase Realtime Database via Firebase Admin SDK.
- **Frontend**: app React (Vite) em `apresentacao/`.

## Requisitos

- Python 3.11+ (testado localmente com 3.12)
- Node.js 18+ (recomendado 20+)
- (Opcional) Docker
- Credenciais do Firebase para acesso ao RTDB (ver seção **Credenciais**)

## Setup rápido (local)

### 1) Backend (FastAPI)

1. Crie/ative um virtualenv e instale dependências:

	```bash
	python -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt
	```

2. Configure variáveis de ambiente criando/ajustando um arquivo `.env` na raiz.

	Variáveis usadas pelo backend (ver `config/settings.py`):

	- `PROJECT_ID` (obrigatório) — ex.: `poshbard`
	- `RTDB_URL` (obrigatório) — ex.: `https://<seu-projeto>-default-rtdb.firebaseio.com`
	- `API_PORT` (opcional, padrão `8000`)
	- `OPENALEX_MAILTO` (opcional)
	- `GOOGLE_APPLICATION_CREDENTIALS` (opcional; ver **Credenciais**)

	Dica: existe um `.env.example` para referência.

3. Suba a API:

	```bash
	uvicorn functions.main:app --reload --host 127.0.0.1 --port ${API_PORT:-8000}
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

	- `VITE_API_URL` (padrão: `http://127.0.0.1:8000`)
	- `VITE_RTDB_URL` (fallback para leitura direta do RTDB em algumas telas)

3. Rode o dev server:

	```bash
	npm run dev
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

## Rodar com Docker (opcional)

O `Dockerfile` sobe o backend via Uvicorn na porta `8080` (ou `PORT`).

```bash
docker build -t poshboard-api .
docker run --rm -p 8080:8080 \
  --env-file .env \
  -e PORT=8080 \
  -v "$PWD/service-account.json:/tmp/service-account.json:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/service-account.json \
  poshboard-api
```

Depois acesse:

- http://127.0.0.1:8080/health

## Firebase Hosting / Emulator (opcional)

O hosting está configurado para publicar `apresentacao/dist` (ver `firebase.json`).

- Build do frontend:

  ```bash
  npm --prefix apresentacao run build
  ```

- Emulator de hosting:

  ```bash
  firebase emulators:start
  ```

## Troubleshooting

- **Erro do Pydantic dizendo que `PROJECT_ID`/`RTDB_URL` não foram informados**: confira seu `.env` na raiz.
- **`DefaultCredentialsError` / problema de credenciais**: ajuste `GOOGLE_APPLICATION_CREDENTIALS` ou faça `gcloud auth application-default login`.
- **Frontend não consegue chamar a API**: confirme `VITE_API_URL` e se a API está em `127.0.0.1:8000` (CORS já permite `localhost:5173`).