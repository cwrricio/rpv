# ADR 0001 — Firestore em vez do Firebase RTDB

**Status:** Decidido  
**Data:** 2026-05-11

## Contexto

O sistema usa Firebase Realtime Database (RTDB) como banco de dados principal. O RTDB apresenta limitações relevantes para o projeto:

- Queries limitadas: só é possível indexar e filtrar por um campo por vez (`order_by_child`). Buscas por ORCID, por exemplo, exigem full scan de toda a coleção.
- Estrutura de JSON aninhado dificulta queries analíticas (rankings, métricas agregadas).
- Parte do código (`autores_merge.py`) já carrega nós inteiros em memória para fazer filtragem manual — sinal de que o modelo não está servindo bem às necessidades.

As alternativas consideradas foram:

1. **Manter RTDB** — sem custo de migração, mas os problemas de query permanecem.
2. **Migrar para Firestore** — mesmo ecossistema Firebase, modelo de documentos com suporte a queries compostas e índices.
3. **Migrar para MongoDB (Atlas)** — maior controle e independência de vendor, mas adiciona complexidade operacional e remove o projeto do ecossistema GCP/Firebase que já sustenta Auth e Hosting.

## Decisão

**Migrar para Firestore.**

## Justificativa

- O projeto já usa Firebase Auth e Firebase Hosting, que continuam sem alteração.
- O Firebase Admin SDK já está inicializado — a troca de API (`db.reference()` → coleções Firestore) é localizada na camada `repositories/`.
- Cloud Run → Firestore é integração nativa no GCP, sem overhead operacional.
- Queries compostas com índices resolvem os full scans atuais.
- MongoDB seria a escolha correta se o objetivo fosse independência total de vendor, o que não é o caso agora.

## Consequências

- A camada `repositories/` (hoje `crud/`) precisa ser reescrita para usar a API do Firestore (`google.cloud.firestore`).
- O restante do código (rotas, services, domain) não muda — desde que o acesso ao banco seja centralizado em `repositories/` antes da migração.
- O `config/firebase_admin_init.py` permanece; o Firestore usa as mesmas credenciais ADC.
- A migração dos dados existentes no RTDB para o Firestore precisa de um script pontual.
