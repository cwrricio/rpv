# ADR 0005 — Handlers síncronos como dívida técnica conhecida

**Status:** Decidido (revisão prevista após ADR 0001)  
**Data:** 2026-05-11

## Contexto

FastAPI é um framework assíncrono construído sobre ASGI (Starlette + Uvicorn). Seu modelo de performance é baseado em `async def` — handlers assíncronos liberam o event loop enquanto aguardam operações de I/O (chamadas de rede, banco de dados), permitindo que o servidor atenda múltiplas requisições simultaneamente sem criar threads adicionais.

Todo o backend atual define handlers como `def` síncrono:

```python
@router.get("")
def listar(svc: DocenteCRUD = Depends(crud)):
    return svc.list()  # chamada bloqueante ao Firebase RTDB
```

Quando um handler síncrono faz uma chamada de rede (ex.: Firebase RTDB via HTTP), ele bloqueia a thread inteira enquanto aguarda a resposta. O FastAPI contorna isso executando handlers `def` em um thread pool interno — mas isso tem custo: criação e gerenciamento de threads, limite de concorrência pelo tamanho do pool.

As alternativas consideradas foram:

1. **Migrar todos os handlers para `async def` agora** — correto tecnicamente, mas exige que todas as chamadas ao Firebase Admin SDK também sejam assíncronas. O SDK atual do Firebase Admin para Python **não tem suporte nativo a async** — seria necessário usar `asyncio.get_event_loop().run_in_executor()` para cada chamada, o que aumenta a complexidade sem ganho real de legibilidade.
2. **Manter `def` síncrono agora, migrar junto com o banco** — a troca para Firestore (ADR 0001) permite usar o cliente oficial assíncrono do Firestore (`google.cloud.firestore_v1.async_client`). Fazer as duas mudanças juntas (banco + async) é mais coeso e menos arriscado do que fazer em separado.

## Decisão

**Manter handlers síncronos agora. Migrar para `async def` na mesma etapa da migração para Firestore (ADR 0001).**

## Justificativa

- O Firebase Admin SDK Python não tem API async nativa. Forçar async agora resultaria em código verboso com `run_in_executor` em cada acesso ao banco — pior do que o estado atual.
- O cliente Python do Firestore (`google-cloud-firestore`) tem suporte async de primeira classe via `AsyncClient`. A migração de banco viabiliza a migração async de forma limpa.
- Para o volume de uso atual (sistema acadêmico, uso intermitente), o thread pool do FastAPI é suficiente. A limitação de performance só se tornaria visível sob carga concorrente alta, que não é o caso agora.
- Fazer as duas mudanças separadas (async agora + banco depois) duplica o esforço de reescrita dos handlers.

## Consequências

- Existe dívida técnica conhecida: handlers síncronos em um servidor ASGI.
- O comportamento é correto — FastAPI executa `def` síncrono em thread pool automaticamente, sem falhas.
- A performance sob carga alta é inferior ao potencial máximo do FastAPI.
- **Gatilho de revisão:** esta decisão deve ser revisitada quando a migração para Firestore (ADR 0001) for executada. Nesse momento, todos os handlers devem ser convertidos para `async def` usando o `AsyncClient` do Firestore.
