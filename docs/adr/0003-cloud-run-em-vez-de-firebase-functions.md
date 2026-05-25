# ADR 0003 — Cloud Run em vez de Firebase Functions para o backend

**Status:** Decidido  
**Data:** 2026-05-11

## Contexto

O projeto usa Firebase como plataforma principal (Auth, Hosting, RTDB). A opção natural para hospedar um backend Python dentro desse ecossistema seria o Firebase Functions (Cloud Functions for Firebase), que oferece deploy simples via `firebase deploy`.

A equipe tentou inicialmente fazer o deploy do backend pelo Firebase. O problema: Firebase Functions não suporta um servidor HTTP de longa duração como o FastAPI com Uvicorn. Firebase Functions é orientado a funções individuais disparadas por evento — cada função tem seu próprio entrypoint, timeout curto e não mantém um processo vivo entre requisições.

FastAPI com Uvicorn é um servidor WSGI/ASGI que precisa de um processo contínuo para gerenciar rotas, middleware, lifespan e conexões. Esse modelo é incompatível com a execução stateless e efêmera do Firebase Functions.

As alternativas consideradas foram:

1. **Firebase Functions** — integração simples com o ecossistema, mas incompatível com FastAPI/Uvicorn.
2. **Cloud Run** — container Docker com processo contínuo, integração nativa com GCP e Firebase, suporte a Uvicorn.
3. **App Engine (Google)** — alternativa mais antiga no GCP, mais configuração, sem vantagem sobre Cloud Run para este caso.
4. **VPS externo (ex.: DigitalOcean, Railway)** — saíria do ecossistema GCP/Firebase, complicaria Auth e credenciais.

## Decisão

**Cloud Run para o backend FastAPI.**

## Justificativa

- Cloud Run executa containers Docker com processo contínuo — modelo compatível com `uvicorn functions.main:app`.
- Integração nativa com GCP: mesmas credenciais ADC usadas pelo Firebase Admin SDK funcionam sem configuração extra.
- Escalonamento automático para zero (sem custo quando ocioso), adequado para um sistema acadêmico com uso intermitente.
- Firebase Hosting pode fazer proxy de rotas `/api/*` para o Cloud Run, mantendo tudo sob o mesmo domínio sem CORS.
- Firebase Auth gera tokens JWT que o Cloud Run pode verificar diretamente com o Firebase Admin SDK.

## Consequências

- O deploy do backend requer um `Dockerfile` e um passo extra além do `firebase deploy` (build e push da imagem).
- Variáveis de ambiente (`PROJECT_ID`, `RTDB_URL`, `OPENALEX_MAILTO`) precisam ser configuradas no Cloud Run, não no Firebase.
- Em ambiente local, continua usando `uvicorn functions.main:app --reload` diretamente.
- CORS deve ser configurado via variável de ambiente para aceitar o domínio do Firebase Hosting em produção.
