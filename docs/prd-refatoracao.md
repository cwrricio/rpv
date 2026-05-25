# PRD — Refatoração do Backend Poshboard

**Data:** 2026-05-11  
**Disciplina:** Manutenção e Evolução de Software  
**Referências:** ADR 0001, 0002, 0003, 0004, 0005 · `CONTEXT.md` · `ARCHITECTURE.md`

---

## Problem Statement

O backend do Poshboard foi desenvolvido durante uma disciplina de graduação sem aplicação sistemática de boas práticas de engenharia de software. O resultado é um código que:

- Possui um bug crítico em produção (`AttributeError` ao buscar Docente por ORCID).
- Duplica a inicialização do banco de dados em mais de cinco arquivos, ignorando o utilitário centralizado que já existe.
- Concentra lógica de negócio (cálculo de métricas bibliométricas como h-index e i10-index) diretamente no arquivo de entrypoint da API.
- Não valida dados de entrada nas rotas, desperdiçando o principal benefício do FastAPI.
- Expõe credenciais de produção no repositório git.
- Possui CORS hardcoded para origens `localhost`, impedindo o deploy sem modificação manual de código.

Esses problemas comprometem a manutenibilidade, a segurança e a capacidade de fazer deploy da aplicação.

---

## Solution

Refatoração dirigida do backend FastAPI, sem reengenharia arquitetural (ADR 0002). As mudanças corrigem bugs, eliminam duplicação, movem código para os lugares certos dentro da estrutura existente e preparam a camada de acesso ao banco para a futura migração ao Firestore (ADR 0001).

A estrutura geral `functions/` + FastAPI é mantida. Nenhuma camada é descartada ou recriada do zero.

---

## User Stories

### Qualidade e Corretude

1. Como desenvolvedor, quero que a busca de Docente por ORCID funcione sem lançar `AttributeError`, para que o sistema consiga associar produções bibliográficas ao Docente correto.
2. Como desenvolvedor, quero que o tipo de um Docente seja validado pelo enum `TipoDocente` definido em `domain/`, para que não existam dois lugares no código definindo os mesmos valores válidos.
3. Como desenvolvedor, quero que a inicialização do banco de dados esteja centralizada em `common/dbref.py`, para que uma mudança de configuração precise ser feita em um único lugar.
4. Como desenvolvedor, quero que `services/analytics.py` contenha a lógica de cálculo de métricas bibliométricas (h-index, h5-index, i10-index), para que `main.py` seja responsável apenas por registrar rotas e configurar middleware.
5. Como desenvolvedor, quero que os handlers de rota não acessem o Firebase Admin SDK diretamente, para que a regra de camadas do `ARCHITECTURE.md` seja respeitada.

### Qualidade FastAPI

6. Como desenvolvedor, quero que os endpoints de criação e atualização de Docentes, Discentes e Projetos validem o corpo da requisição com modelos Pydantic, para que erros de formato sejam rejeitados antes de chegar ao banco de dados.
7. Como desenvolvedor, quero que os endpoints declarem `response_model`, para que o Swagger/OpenAPI gerado automaticamente pelo FastAPI reflita o contrato real da API.
8. Como desenvolvedor, quero que a instância do repositório de cada entidade seja criada via `lru_cache`, para que o padrão global mutável `_crud = None` seja eliminado de todos os arquivos de rota.
9. Como desenvolvedor, quero que `HTTPException` seja importada apenas uma vez no topo de cada arquivo, para que não existam reimportações dentro de funções.

### Segurança e Deploy

10. Como desenvolvedor, quero que `service-account.json` não esteja rastreado pelo git, para que credenciais de produção não fiquem expostas no repositório.
11. Como operador de deploy, quero configurar as origens CORS permitidas via variável de ambiente `CORS_ORIGINS`, para que o mesmo container funcione em desenvolvimento e produção sem alteração de código.
12. Como desenvolvedor, quero que o repositório não contenha arquivos de conflito de merge (`package_BACKUP_379.json`, `package_BASE_379.json`, `package_LOCAL_379.json`, `package_REMOTE_379.json`), para que o estado do repositório seja limpo e apresentável.

### Nomenclatura e Navegabilidade

13. Como desenvolvedor, quero que a pasta `crud/` se chame `repositories/`, para que o nome reflita o papel arquitetural da pasta (repositório de acesso a dados, não um acrônimo de operações).
14. Como desenvolvedor, quero que o typo `commom/` seja corrigido para `common/`, para que as importações e a navegação no repositório sejam consistentes.

### Preparação para Evolução

15. Como desenvolvedor, quero que todo acesso ao banco de dados passe pela camada `repositories/`, para que a futura migração ao Firestore (ADR 0001) exija mudanças apenas nessa pasta.

---

## Implementation Decisions

### Módulos modificados

**`common/dbref.py`** (renomeado de `commom/`)
- Único ponto de inicialização do Firebase Admin SDK e retorno de referências RTDB.
- Interface mantida: `ref(path: str)`.
- Todos os outros módulos que definem `_db()` inline passam a importar daqui.

**`repositories/`** (renomeado de `crud/`)
- `BaseCRUD` mantém sua interface atual (`create`, `list`, `get`, `update`, `delete`).
- Bug corrigido: `self._node()` → `self.ref()` em `DocenteCRUD.find_by_orcid`.
- `DocenteCRUD` passa a usar `TipoDocente` de `domain/types.py` em vez de `TIPOS_VALIDOS`.
- Nenhuma outra lógica é adicionada — a camada permanece exclusivamente de acesso a dados.

**`services/analytics.py`**
- Recebe a lógica extraída de `main.py`: cálculo de h-index, h5-index, i10-index, agregação de publicações por autor.
- Interface pública: função `compute_author_metrics(author_id: str) -> dict`.
- `main.py` passa a chamar essa função no handler `/autores/{id}/metrics`.

**`domain/schemas.py`** *(arquivo novo)*
- Modelos Pydantic para as entidades principais: `DocenteCreate`, `DocenteOut`, `DiscenteCreate`, `DiscenteOut`, `ProjetoCreate`, `ProjetoOut`.
- Os modelos usam os enums de `domain/types.py` para campos como `tipo` de Docente e `status` de Pesquisa.

**`api_routes/`**
- Handlers dos endpoints de Docente, Discente e Projeto passam a usar os modelos Pydantic de `domain/schemas.py`.
- Singleton global `_crud = None` substituído por `@lru_cache` em função de fábrica.
- `HTTPException` importada apenas no topo de cada arquivo.
- `api_routes/produtos.py`: acesso direto ao Firebase removido do handler `/ranking`; lógica extraída para `services/`.

**`main.py`**
- Lógica de negócio de métricas removida; handler delega para `services/analytics.py`.
- CORS configurado via variável de ambiente `CORS_ORIGINS` (lista separada por vírgula).
- Importações de `HTTPException` consolidadas no topo do arquivo.

**`.gitignore`**
- `service-account.json` adicionado.
- Arquivos de conflito de merge removidos do rastreamento.

### Interfaces que não mudam

- Contratos HTTP existentes (paths, métodos, campos de resposta) são preservados — a refatoração não quebra clientes existentes.
- `config/firebase_admin_init.py` permanece sem alteração.
- `ingest/`, `workers/` e `jobs/` não são modificados nesta etapa.

---

## Testing Decisions

### O que constitui um bom teste neste projeto

Um bom teste verifica o comportamento externo observável de um módulo, não sua implementação interna. Para este projeto:

- Testes de `repositories/` devem verificar que os dados corretos são escritos e lidos do banco, não que métodos internos foram chamados.
- Testes de `services/analytics.py` devem verificar que, dado um conjunto de publicações com citações conhecidas, os índices calculados estão corretos — sem depender de Firebase.
- Testes de rotas devem verificar status HTTP e estrutura de resposta, usando um cliente de teste FastAPI (`TestClient`).

### Módulos com testes prioritários

| Módulo | Tipo de teste | Justificativa |
|---|---|---|
| `services/analytics.py` | Unitário (puro Python) | Lógica de cálculo de índices é determinística e não depende de I/O — fácil de testar em isolamento. |
| `repositories/BaseCRUD` | Integração com emulador Firebase | Verifica create/list/get/update/delete contra comportamento real do banco. |
| `api_routes/docentes.py` | Teste de rota com `TestClient` | Verifica validação Pydantic, status codes e que `find_by_orcid` não lança `AttributeError`. |
| `domain/schemas.py` | Unitário (Pydantic) | Verifica que valores inválidos de `TipoDocente` são rejeitados na criação de Docente. |

---

## Out of Scope

- **Migração para Firestore** — decidida em ADR 0001, mas depende desta refatoração como pré-condição. Não ocorre nesta etapa.
- **Conversão de handlers para `async def`** — decidida em ADR 0005 para ocorrer junto com a migração Firestore.
- **Agente Lattes** — mencionado em `ARCHITECTURE.md` como próximo adapter de ingest. Fora do escopo de manutenção.
- **Autenticação JWT no backend** — `ARCHITECTURE.md` menciona verificação de ID Token, mas não está implementada e não faz parte desta refatoração.
- **Reengenharia arquitetural** — explicitamente descartada em ADR 0002.
- **Modificações no frontend** (`apresentacao/`) — fora do escopo desta etapa.

---

## Further Notes

- A ordem de execução importa: a renomeação de `crud/` → `repositories/` e `commom/` → `common/` deve ser feita em um único commit com atualização de todos os imports, para evitar estado intermediário quebrado.
- O `service-account.json` deve ser removido do histórico git com `git filter-repo` ou `BFG Repo Cleaner`, não apenas do `.gitignore`. Credenciais já expostas devem ser rotacionadas no Firebase Console.
- A variável `CORS_ORIGINS` deve ser documentada no `README.md` e no `ARCHITECTURE.md` para que futuros deploys não quebrem por falta de configuração.
- Os ADRs 0001–0005 em `docs/adr/` e o `CONTEXT.md` são documentação viva — devem ser atualizados conforme decisões evoluem.
