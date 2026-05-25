# Frentes de Refatoração — Poshboard

**Data:** 2026-05-24
**Referências:** `docs/prd-refatoracao.md` · `docs/relatorio-refatoracao.md` · ADR 0001–0005

---

## Frente 1 — Infraestrutura e Segurança

**Foco:** limpeza do repositório, segurança de credenciais e configuração de deploy.

| # | Atividade | Arquivo(s) |
|---|---|---|
| 1.1 | Remover `service-account.json` do histórico git (`git filter-repo` ou BFG) e rotacionar credenciais no Firebase Console | `.gitignore` + histórico git |
| 1.2 | Adicionar `service-account.json` ao `.gitignore` | `.gitignore` |
| 1.3 | Configurar CORS via variável de ambiente `CORS_ORIGINS` (lista separada por vírgula) em vez de hardcoded | `functions/main.py` |
| 1.4 | Documentar a variável `CORS_ORIGINS` no `README.md` e no `ARCHITECTURE.md` | `README.md`, `docs/ARCHITECTURE.md` |
| 1.5 | Remover arquivos de conflito de merge do repositório (`package_BACKUP_379.json`, `package_BASE_379.json`, `package_LOCAL_379.json`, `package_REMOTE_379.json`) | `apresentacao/` |

---

## Frente 2 — Renomeação, Centralização e Correção de Bug Crítico

**Foco:** renomear pastas, centralizar inicialização do banco e corrigir o bug de produção.

| # | Atividade | Arquivo(s) |
|---|---|---|
| 2.1 | Renomear `commom/` → `common/` e atualizar todos os imports (em único commit) | toda a pasta `commom/` + imports |
| 2.2 | Renomear `crud/` → `repositories/` e atualizar todos os imports (em único commit) | toda a pasta `crud/` + imports |
| 2.3 | Corrigir bug crítico: `self._node()` → `self.ref()` em `DocenteCRUD.find_by_orcid` | `repositories/docente_crud.py:20` |
| 2.4 | Centralizar `_db()` em `common/dbref.py` — remover as 5+ redefinições espalhadas | `api_routes/autores_merge.py`, `api_routes/autores_flat.py`, `ingest/openalex.py`, `workers/upsert.py`, `workers/resolvers.py` |
| 2.5 | Substituir `TIPOS_VALIDOS` (set local) pelo enum `TipoDocente` de `domain/types.py` em `docente_crud.py` | `repositories/docente_crud.py` |

---

## Frente 3 — Qualidade FastAPI (Rotas e Dependências)

**Foco:** modernizar os endpoints com Pydantic, `lru_cache` e `response_model`.

| # | Atividade | Arquivo(s) |
|---|---|---|
| 3.1 | Criar `domain/schemas.py` com modelos Pydantic: `DocenteCreate`, `DocenteOut`, `DiscenteCreate`, `DiscenteOut`, `ProjetoCreate`, `ProjetoOut` (usando enums de `domain/types.py`) | `domain/schemas.py` *(novo)* |
| 3.2 | Substituir `body: dict` por modelos Pydantic nos endpoints de Docentes, Discentes e Projetos | `api_routes/docentes.py`, `api_routes/discentes.py`, `api_routes/projetos.py` |
| 3.3 | Adicionar `response_model=` em todos os endpoints afetados | `api_routes/docentes.py`, `api_routes/discentes.py`, `api_routes/projetos.py` |
| 3.4 | Substituir o padrão `_crud = None` + global mutable por `@lru_cache` em todos os arquivos de rota | todos os arquivos em `api_routes/` que usam o padrão |
| 3.5 | Consolidar importações de `HTTPException` no topo de cada arquivo (remover reimportações dentro de funções) | `main.py` + arquivos de rota afetados |
| 3.6 | Remover acesso direto ao Firebase Admin SDK em `api_routes/produtos.py` (handler `/ranking`) — extrair lógica para `services/` | `api_routes/produtos.py` |

---

## Frente 4 — Camada de Serviços e Testes ✅ CONCLUÍDA (2026-05-25)

**Foco:** mover lógica de negócio para o lugar certo e cobrir os módulos críticos com testes.
**Detalhamento da implementação:** ver `docs/frente 4.md`.

| # | Atividade | Status | Arquivo(s) |
|---|---|---|---|
| 4.1 | Extrair lógica de h-index, h5-index, i10-index e agregação de publicações de `main.py` para `services/analytics.py` | ✅ | `functions/main.py`, `functions/services/analytics.py` |
| 4.2 | Fazer handler `/autores/{id}/metrics` em `main.py` delegar para `services/analytics.compute_author_metrics()` | ✅ | `functions/main.py` |
| 4.3 | Escrever testes unitários para `services/analytics.py` (dado conjunto de publicações com citações conhecidas → índices corretos, sem Firebase) | ✅ | `tests/test_analytics.py` |
| 4.4 | Escrever testes de rota para `api_routes/docentes.py` com `TestClient` — verificar validação Pydantic, status codes e que `find_by_orcid` não lança `AttributeError` | ✅ | `tests/test_docentes.py` |
| 4.5 | Escrever testes unitários Pydantic para `domain/schemas.py` — verificar rejeição de `TipoDocente` inválido | ✅ | `tests/test_schemas.py` |
| 4.6 | Escrever testes de integração para `BaseCRUD` (create/list/get/update/delete) — fake em memória + emulador Firebase opt-in | ✅ | `tests/test_base_crud.py` |

> **Notas:** (1) `h5_index` e `i10_index` não existiam no handler original — foram
> implementados nesta frente. (2) A correção do bug `self._node()` → `self.ref()`
> (Frente 2.3) precisou ser aplicada como pré-requisito do teste 4.4, pois a
> Frente 2 ainda não estava mergeada nesta branch. (3) Nesta branch as pastas
> ainda são `crud/` e `commom/` (renomeação é da Frente 2); o conteúdo dos testes
> e do serviço independe da renomeação. **Resultado:** `54 passed, 1 skipped`.

---

## Dependências entre frentes

```
Frente 1 ──────────────────────────────► independente, pode começar já
Frente 2 ──► Frente 3 ──► Frente 4
              (schemas)     (testes)
```

- **Frente 1** é independente e pode rodar em paralelo com qualquer outra desde o início.
- **Frente 2** deve ser concluída antes das Frentes 3 e 4, para que os imports estejam estabilizados.
- **Frente 3** (item 3.1 — criação de `domain/schemas.py`) deve estar concluída antes da Frente 4 iniciar os testes de schemas e rotas.
