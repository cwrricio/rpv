# Relatório de Análise: Refatoração vs. Reengenharia — Poshboard

**Data:** 2026-05-11  
**Projeto:** Poshboard — Sistema de Gestão de Pós-Graduação  
**Disciplina:** Manutenção e Evolução de Software  
**Escopo:** Backend FastAPI (`functions/`) + decisões arquiteturais

---

## 1. Contexto

O projeto Poshboard foi desenvolvido durante uma disciplina de graduação com o objetivo de gerenciar professores, projetos, bolsas e publicações acadêmicas de um programa de pós-graduação. O sistema coleta dados de APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar), gera métricas bibliométricas e produz relatórios exportáveis.

A stack atual é:

- **Frontend:** React + Vite, hospedado no Firebase Hosting
- **Backend:** FastAPI (Python), entrypoint em `functions/main.py`
- **Banco de dados:** Firebase Realtime Database (RTDB)
- **Auth:** Firebase Authentication
- **Deploy:** Cloud Run (backend) + Firebase Hosting (frontend)
- **Jobs agendados:** Cloud Scheduler + Cloud Run Jobs

---

## 2. Questão central: Reengenharia ou Refatoração?

### 2.1 Definições

| Termo | Definição aplicada |
|---|---|
| **Reengenharia** | Redesenho completo da arquitetura: novas pastas, novos contratos entre camadas, nova estrutura de deploy, descarte substancial do código existente. |
| **Refatoração** | Melhorias internas no código existente que não alteram o comportamento externo: correção de bugs, eliminação de duplicação, reorganização de responsabilidades dentro da estrutura já existente. |

### 2.2 Avaliação

A análise do código revelou que **os problemas encontrados são de qualidade interna, não de arquitetura**. A estrutura geral `functions/` + FastAPI é funcional e está alinhada com a proposta documentada em `ARCHITECTURE.md`. A reengenharia não é justificada porque:

1. A estrutura de camadas proposta (`api_routes → services → repositories → Firebase`) já existe — o que falta é o código respeitá-la, não redesenhá-la.
2. Reengenharia em um projeto com histórico de desenvolvimento activo tem alto risco de regressões sem benefício proporcional.
3. Todos os problemas identificados (bugs, duplicação, lógica fora do lugar) são resolvíveis com refatoração localizada.

**Conclusão: refatoração é suficiente.**

---

## 3. Análise da Arquitetura Atual

### 3.1 Estrutura de pastas

```
functions/
├── main.py              ← entrypoint FastAPI
├── api_routes/          ← handlers HTTP (docentes, discentes, projetos...)
├── crud/                ← acesso ao RTDB (BaseCRUD + implementações)
├── domain/              ← tipos e enums (TipoDocente, StatusPesquisa)
├── ingest/              ← clientes HTTP externos (OpenAlex, ORCID, Crossref, S2)
├── jobs/                ← entrypoints de cron
├── services/            ← lógica de negócio (quase vazio)
├── workers/             ← processamento em lote
└── commom/              ← utilitários compartilhados (typo)
```

### 3.2 Camadas propostas em `ARCHITECTURE.md`

```
[Interface]        api_routes/ + jobs/
      ↓
[Aplicação]        services/ + workers/
      ↓
[Domínio]          domain/
      ↓
[Infraestrutura]   crud/ + ingest/ + config/
```

### 3.3 Violações identificadas

| Violação | Arquivo | Descrição |
|---|---|---|
| Lógica de negócio na interface | `main.py:100–206` | Cálculo de h-index, h5-index, i10-index e agregação de publicações diretamente no handler de rota. Deveria estar em `services/analytics.py`. |
| Acesso ao banco fora do repositório | `api_routes/produtos.py:29–58` | Endpoint acessa o Firebase Admin SDK diretamente, pulando a camada `crud/`. |
| `services/analytics.py` vazio | `services/analytics.py` | Arquivo existe apenas com `# TODO: implementar`. A lógica correspondente está em `main.py`. |

---

## 4. Problemas Encontrados

### 4.1 Bug crítico

**`functions/crud/docente_crud.py`, linha 20**

```python
def find_by_orcid(self, orcid: str) -> List[Dict]:
    node = self._node()  # AttributeError: método não existe em BaseCRUD
```

`BaseCRUD` expõe apenas `self.ref()`. O método `_node()` não está definido em nenhum lugar da hierarquia. Toda chamada a `find_by_orcid` resulta em `AttributeError` em produção.

**Correção:** substituir `self._node()` por `self.ref()`.

---

### 4.2 Duplicação de código

**`_db()` redefinida em 5+ arquivos**

A função que inicializa o Firebase e retorna o cliente do banco é redefinida manualmente em cada módulo:

| Arquivo | Linha |
|---|---|
| `api_routes/autores_merge.py` | 7–11 |
| `api_routes/autores_flat.py` | 18–23 |
| `ingest/openalex.py` | 12–17 |
| `workers/upsert.py` | 9–18 |
| `workers/resolvers.py` | 2–24 (5 variantes) |

`functions/commom/dbref.py` já existe com essa função centralizada e está sendo ignorado por todo o código:

```python
# commom/dbref.py — existe, mas ninguém usa
def ref(path: str):
    init_firebase()
    return db.reference(path)
```

**Correção:** todos os módulos passam a importar de `common/dbref.py`.

---

### 4.3 Inconsistência de domínio

**`TipoDocente` definido em dois lugares**

`functions/domain/types.py` define:

```python
class TipoDocente(str, Enum):
    PERMANENTE = "PERMANENTE"
    COLABORADOR = "COLABORADOR"
    VISITANTE = "VISITANTE"
```

`functions/crud/docente_crud.py` ignora o enum e define seu próprio conjunto:

```python
TIPOS_VALIDOS = {"PERMANENTE", "COLABORADOR", "VISITANTE"}  # duplicado
```

**Correção:** `docente_crud.py` passa a importar e usar `TipoDocente` de `domain/types.py`.

---

### 4.4 Problemas de segurança e deploy

| Problema | Impacto |
|---|---|
| `service-account.json` rastreado pelo git | Credenciais de produção expostas no repositório |
| CORS hardcoded em `main.py` com origens `localhost` | Qualquer ambiente de deploy diferente quebra sem alteração de código |
| Arquivos de conflito de merge no repositório (`package_BACKUP_379.json`, `package_BASE_379.json`, `package_LOCAL_379.json`, `package_REMOTE_379.json`) | Repositório com artefatos de desenvolvimento, não profissional |
| Typo `commom/` no nome da pasta | Apresentação e importações inconsistentes |

---

## 5. Sugestões de Refatoração FastAPI

As sugestões abaixo são específicas do framework FastAPI e representam o uso correto das funcionalidades que ele oferece.

### 5.1 Pydantic em vez de `body: dict`

**Situação atual:** todos os endpoints aceitam dados sem validação.

```python
# atual — sem validação, sem documentação automática
@router.post("", status_code=201)
def criar(body: dict, svc: DocenteCRUD = Depends(crud)):
    return svc.create(body)
```

**Situação proposta:** modelos Pydantic definidos em `domain/`.

```python
# proposto
from domain.schemas import DocenteCreate

@router.post("", status_code=201, response_model=DocenteOut)
def criar(body: DocenteCreate, svc: DocenteCRUD = Depends(crud)):
    return svc.create(body.model_dump())
```

**Benefícios:** validação automática, mensagens de erro padronizadas, documentação OpenAPI gerada automaticamente, tipagem de resposta.

---

### 5.2 Handlers síncronos bloqueando o event loop

**Situação atual:** todas as rotas são `def` síncronos. Chamadas ao Firebase (I/O de rede) bloqueiam o processo enquanto esperam resposta.

```python
# atual — bloqueia o event loop
@router.get("")
def listar(svc: DocenteCRUD = Depends(crud)):
    return svc.list()
```

**Situação proposta:** `async def` com chamadas síncronas executadas em thread pool via `run_in_executor`, ou migração para o cliente assíncrono do Firestore (quando a migração de banco ocorrer).

---

### 5.3 Singleton global frágil para dependências

**Situação atual:** padrão caseiro de lazy singleton global em cada arquivo de rota.

```python
# atual — em cada arquivo de rota
_crud: Optional[DocenteCRUD] = None

def crud() -> DocenteCRUD:
    global _crud
    if _crud is None:
        _crud = DocenteCRUD()
    return _crud
```

**Situação proposta:** usar `lru_cache` para garantir instância única de forma idiomática, ou injetar via `Depends()` diretamente sem estado global.

```python
from functools import lru_cache

@lru_cache
def get_docente_crud() -> DocenteCRUD:
    return DocenteCRUD()
```

---

### 5.4 Lógica de negócio em `main.py`

**Situação atual:** `main.py` contém 100 linhas de lógica de negócio (cálculo de métricas bibliométricas) dentro de um handler de rota.

**Situação proposta:** extrair para `services/analytics.py`, que já existe mas está vazio. O handler fica com sua única responsabilidade: receber a requisição, chamar o serviço, retornar a resposta.

---

### 5.5 Ausência de `response_model`

**Situação atual:** nenhum endpoint declara o modelo de saída. O FastAPI não valida nem documenta o que é retornado.

**Situação proposta:** todos os endpoints usam `response_model=` para garantir que a resposta está no formato esperado e que o Swagger/OpenAPI está correto.

---

### 5.6 Importações inconsistentes de `HTTPException`

**Situação atual:** `HTTPException` é importada no topo de `main.py` e reimportada dentro de funções individuais.

```python
from fastapi import FastAPI, HTTPException  # importação no topo

# ...mais adiante, dentro de uma função:
from fastapi import HTTPException  # reimportação desnecessária
raise HTTPException(status_code=502, detail=f"RTDB error: {e}")
```

**Situação proposta:** uma única importação no topo de cada arquivo.

---

## 6. Mudanças Propostas na Estrutura de Pastas

As seguintes renomeações são manutenção de nomenclatura, sem alterar comportamento.

| Atual | Proposto | Justificativa |
|---|---|---|
| `functions/crud/` | `functions/repositories/` | `crud` é um acrônimo de operações; `repositories` nomeia o papel arquitetural correto da pasta (repositório de acesso a dados). |
| `functions/commom/` | `functions/common/` | Correção de typo. |

O restante da estrutura de pastas permanece igual.

---

## 7. Decisão de Banco de Dados

### 7.1 Problema com Firebase RTDB

O Firebase Realtime Database apresenta limitações que já estão causando código ruim:

- Queries limitadas a um único índice por vez (`order_by_child`).
- Buscas por campo (ex.: ORCID) exigem carregar toda a coleção em memória e filtrar manualmente — como ocorre em `api_routes/autores_merge.py:22–28`.
- Estrutura de JSON aninhado dificulta queries analíticas complexas (rankings, métricas).

### 7.2 Decisão: migrar para Firestore

**Firestore** foi escolhido como substituto ao invés de MongoDB pelos seguintes motivos:

- Permanece no ecossistema Firebase (Auth e Hosting não mudam).
- Firebase Admin SDK já está inicializado — a mudança fica localizada na camada `repositories/`.
- Integração nativa com Cloud Run no GCP.
- Suporte a queries compostas com índices, resolvendo os problemas atuais de full scan.

A migração **não ocorre agora**. A pré-condição é centralizar o acesso ao banco em `repositories/` (refatoração atual), de forma que quando a troca de banco ocorrer, apenas essa pasta precise mudar.

---

## 8. Resumo das Mudanças

### Imediatas (refatoração)

| # | Mudança | Arquivo(s) | Tipo |
|---|---|---|---|
| 1 | Corrigir `self._node()` → `self.ref()` | `crud/docente_crud.py` | Bug |
| 2 | Centralizar `_db()` em `common/dbref.py` | 5+ arquivos | Duplicação |
| 3 | Mover lógica de métricas de `main.py` para `services/analytics.py` | `main.py`, `services/analytics.py` | Coesão |
| 4 | Substituir `TIPOS_VALIDOS` por `TipoDocente` enum | `crud/docente_crud.py` | Inconsistência |
| 5 | Renomear `crud/` → `repositories/` | Toda a pasta | Nomenclatura |
| 6 | Renomear `commom/` → `common/` | Toda a pasta | Typo |
| 7 | Remover `service-account.json` do git | `.gitignore` + histórico | Segurança |
| 8 | CORS via variável de ambiente | `main.py` | Configurabilidade |
| 9 | Remover arquivos de conflito de merge | `apresentacao/` | Limpeza |
| 10 | Adicionar modelos Pydantic nos endpoints principais | `api_routes/`, `domain/` | Qualidade FastAPI |

### Futuras (evolução)

| # | Mudança | Dependência |
|---|---|---|
| 11 | Migrar `repositories/` de RTDB para Firestore | Item 5 concluído |
| 12 | Tornar handlers `async def` | Item 11 (cliente Firestore async) |

---

## 9. Documentação Gerada nesta Sessão

| Arquivo | Conteúdo |
|---|---|
| `CONTEXT.md` | Glossário de domínio: Docente, Discente, Produto, Veículo, Pesquisa, Harvest, Raw/Canonical, métricas |
| `docs/adr/0001-firestore-em-vez-de-rtdb.md` | Decisão de banco: Firestore vs RTDB vs MongoDB |
| `docs/adr/0002-manutencao-sem-reengenharia.md` | Decisão de escopo: refatoração vs reengenharia |
| `docs/relatorio-refatoracao.md` | Este documento |
