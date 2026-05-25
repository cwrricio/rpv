# ARCHITECTURE — Poshboard

Visão geral da arquitetura do sistema, decisões de design e variáveis de ambiente relevantes.

---

## Visão Geral

```
┌──────────────────────────────────────────────────────┐
│                      Frontend                        │
│         React (Vite) · apresentacao/                 │
│         Serve via Firebase Hosting                   │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP (VITE_API_URL)
┌────────────────────▼─────────────────────────────────┐
│                      Backend                         │
│         FastAPI (Python) · functions/main.py         │
│         Roda via Uvicorn (local) ou Cloud Run        │
└────────────────────┬─────────────────────────────────┘
                     │ Firebase Admin SDK
┌────────────────────▼─────────────────────────────────┐
│              Firebase Realtime Database               │
│         (poshbard-default-rtdb.firebaseio.com)       │
└──────────────────────────────────────────────────────┘
```

---

## Backend — FastAPI

### Estrutura de pastas

```
functions/
  main.py               # Entry point: app FastAPI, middlewares, routers
  api_routes/           # Endpoints REST organizados por domínio
  ingest/               # Integrações externas (OpenAlex, ORCID, CrossRef…)
  crud/                 # Operações de leitura/escrita no RTDB
  domain/               # Tipos e modelos de domínio
  services/             # Lógica de negócio reutilizável
  workers/              # Processamento assíncrono / batch
config/
  firebase_admin_init.py  # Inicialização única do Firebase Admin SDK
  settings.py             # Leitura de variáveis de ambiente via Pydantic
```

---

## Variáveis de Ambiente

Todas as variáveis são carregadas de um arquivo `.env` na raiz (via `python-dotenv`).  
**Nunca commitar o `.env` ou qualquer arquivo de credenciais.**

### Backend

| Variável | Obrigatório | Padrão | Descrição |
|---|---|---|---|
| `PROJECT_ID` | ✅ | — | ID do projeto Firebase (ex.: `poshbard`) |
| `RTDB_URL` | ✅ | — | URL do Realtime Database |
| `GOOGLE_APPLICATION_CREDENTIALS` | Recomendado | ADC do ambiente | Caminho para o JSON de service account |
| `API_PORT` | Não | `8000` | Porta em que o Uvicorn sobe |
| `OPENALEX_MAILTO` | Não | — | E-mail para o polite pool do OpenAlex |
| `CORS_ORIGINS` | Não¹ | origens localhost | Origens CORS separadas por vírgula |

¹ Em **produção** é obrigatório definir `CORS_ORIGINS` explicitamente.

### CORS — detalhes

A variável `CORS_ORIGINS` controla quais origens o backend aceita via header `Access-Control-Allow-Origin`.

```
# .env (exemplo)
CORS_ORIGINS=http://localhost:5173,https://meu-app.web.app,https://meu-dominio.com
```

- Cada origem deve ser uma URL completa (scheme + host + porta se não-padrão).
- Se a variável estiver vazia ou ausente, o backend usa uma lista padrão de origens `localhost` para desenvolvimento.
- **Nunca** configure `allow_origins=["*"]` junto com `allow_credentials=True` — isso viola a especificação CORS e é rejeitado pelos browsers.

### Frontend (Vite)

| Variável | Padrão | Descrição |
|---|---|---|
| `VITE_API_URL` | `http://127.0.0.1:8000` | URL base do backend |
| `VITE_RTDB_URL` | — | Fallback para leitura direta do RTDB |

---

## Segurança — Credenciais

### Regras obrigatórias

1. **`service-account.json` nunca entra no repositório.** Está listado no `.gitignore`.
2. Se um arquivo de credenciais foi commitado por engano, o procedimento é:
   a. Remover do histórico com `git filter-repo` ou BFG Repo Cleaner.
   b. **Rotacionar imediatamente** a service account no Firebase Console (criar nova chave, revogar a antiga).
3. Em CI/CD (GitHub Actions), credenciais são injetadas via **Secrets** do repositório — nunca em texto claro no workflow.
4. Em produção (Cloud Run / GCE), usar **Workload Identity Federation** ou variáveis de ambiente seguras — não montar arquivos JSON em imagens Docker.

---

## Deploy

### Firebase Hosting (frontend)

```bash
npm --prefix apresentacao run build
firebase deploy --only hosting
```

### Backend (Cloud Run — exemplo)

```bash
gcloud run deploy poshboard-api \
  --source . \
  --region southamerica-east1 \
  --set-env-vars "PROJECT_ID=poshbard,RTDB_URL=https://poshbard-default-rtdb.firebaseio.com,CORS_ORIGINS=https://meu-app.web.app"
```

> As credenciais do Firebase Admin SDK em Cloud Run devem ser fornecidas via Workload Identity ou variável `GOOGLE_APPLICATION_CREDENTIALS` apontando para um Secret Manager secret montado como volume.

---

## Arquivos que NUNCA devem ser commitados

| Arquivo / padrão | Motivo |
|---|---|
| `service-account.json` | Credenciais de produção do Firebase |
| `*.firebase.json` (exceto `firebase.json`) | Pode conter tokens |
| `.env`, `.env.local` | Segredos e configurações locais |
| `*_BACKUP_*.json`, `*_BASE_*.json`, `*_LOCAL_*.json`, `*_REMOTE_*.json` | Artefatos de conflito de merge do git |
| `*.orig` | Artefatos de merge |

Todos os padrões acima estão declarados no `.gitignore` da raiz.
