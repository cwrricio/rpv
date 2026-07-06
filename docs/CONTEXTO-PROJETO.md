# Poshboard — Contexto Completo do Projeto

> Documento único e exaustivo sobre o projeto: ideia, arquitetura, dados, código, decisões, histórico e dívida técnica. Consolida `README.md`, `APRESENTACAO.md`, `docs/ARCHITECTURE.md`, `docs/CLAUDE.MD`, `docs/brainstorming.md`, `docs/prd-refatoracao.md`, `docs/relatorio-refatoracao.md`, `docs/frentes-refatoracao.md`, `docs/frente 4.md`, `docs/adr/*`, `docs/plano-migracao-poshboard-llm.md`, `relatorio-final-ssqm/*` e leitura direta do código-fonte atual (2026-07-06).
>
> Onde a documentação existente diverge do código, este documento assinala o estado **real** do código e marca a divergência explicitamente.

---

## Índice

1. [O que é o Poshboard](#1-o-que-é-o-poshboard)
2. [Contexto acadêmico e histórico do projeto](#2-contexto-acadêmico-e-histórico-do-projeto)
3. [Objetivos do produto](#3-objetivos-do-produto)
4. [Stack tecnológica](#4-stack-tecnológica)
5. [Arquitetura](#5-arquitetura)
6. [Estrutura de pastas completa](#6-estrutura-de-pastas-completa)
7. [Modelo de dados](#7-modelo-de-dados)
8. [API — todos os endpoints](#8-api--todos-os-endpoints)
9. [Pipeline de ingestão acadêmica](#9-pipeline-de-ingestão-acadêmica)
10. [Métricas bibliométricas (analytics)](#10-métricas-bibliométricas-analytics)
11. [Frontend (`apresentacao/`)](#11-frontend-apresentacao)
12. [Testes](#12-testes)
13. [Configuração, segurança e deploy](#13-configuração-segurança-e-deploy)
14. [Decisões arquiteturais (ADRs)](#14-decisões-arquiteturais-adrs)
15. [Histórico de refatoração (Frentes 1–4)](#15-histórico-de-refatoração-frentes-14)
16. [Relatório de Soberania de Software (SSQM)](#16-relatório-de-soberania-de-software-ssqm)
17. [Plano de migração + experimento com LLMs](#17-plano-de-migração--experimento-com-llms)
18. [Achados adicionais — código morto e duplicações não documentadas](#18-achados-adicionais--código-morto-e-duplicações-não-documentadas)
19. [Dívida técnica e pontos de melhoria conhecidos](#19-dívida-técnica-e-pontos-de-melhoria-conhecidos)
20. [Glossário](#20-glossário)

---

## 1. O que é o Poshboard

**Poshboard** (nome interno do repositório: `rpv`; projeto Firebase: `poshbard`) é um **dashboard de gestão e acompanhamento de produção acadêmica para programas de pós-graduação**. Ele centraliza dados de docentes, discentes, projetos de pesquisa, linhas de pesquisa, veículos de publicação (journals/conferências) e produções científicas, enriquecendo tudo automaticamente a partir de APIs acadêmicas externas.

Ideia central, nas palavras originais do time (`docs/brainstorming.md` / `docs/CLAUDE.MD`):

> 1. Gerencia professores, programas de pesquisa, projetos, bolsas.
> 2. Atualiza dados acadêmicos como publicações a partir de APIs como OpenAlex. Utiliza também Agentes de IA (agno) para buscar dados na web e conseguir os dados de autores via currículo Lattes (forma de webscraping).
> 3. Gera gráficos e relatórios de análise de dados que podem ser exportados para plataformas como Sucupira.

**Estado real de implementação desses três pontos:**

| Ponto da ideia original | Implementado? |
|---|---|
| Gestão de docentes/discentes/projetos/linhas/veículos | ✅ CRUD completo para todas as entidades |
| Ingestão de publicações via OpenAlex | ✅ implementado (vários adapters, ver seção 9) |
| Ingestão via ORCID, Crossref, Semantic Scholar | ✅ implementado |
| Agente de IA (framework "agno") para scraping do Lattes | ❌ **não implementado**. Não há nenhuma referência a `agno` nem a scraping de Lattes em nenhum arquivo `.py` do projeto — é uma intenção documentada, não código. `docs/ARCHITECTURE.md` já antecipa isso como "próximo adapter": `functions/ingest/lattes/` (pasta que também não existe ainda). |
| Gráficos/relatórios | ✅ parcial — frontend tem páginas de relatório (`Report`, `RelatorioProducao`, `Qualis`) e libs de gráfico (Chart.js/Recharts), mas exportação para Sucupira **não existe** |
| Exportação para Sucupira | ❌ não implementada |

O fluxo de dados de ponta a ponta:

```
APIs Externas ──► Ingestão ──► Banco (Firebase RTDB) ──► API REST (FastAPI) ──► Frontend React
(OpenAlex, ORCID,     (raw → canonical,       /autores, /docentes,
 Crossref, S2)         ver seção 7)            /autores_flat, /produtos...
```

---

## 2. Contexto acadêmico e histórico do projeto

O projeto **nasceu em uma disciplina de graduação** e foi construído sem aplicação sistemática de boas práticas de engenharia de software (nas palavras do próprio time: "foi mal feito"). Depois, o projeto passou a ser objeto de uma **disciplina de Manutenção e Evolução de Software**, na qual a pergunta inicial era: *reengenharia completa* (trocar para "backend as a service" → arquitetura em camadas do zero) ou *manutenção dirigida*?

A decisão registrada (ADR 0002) foi **manutenção sem reengenharia**: a estrutura `functions/` + FastAPI + Firebase já é funcional e já reflete (na intenção) uma arquitetura em camadas — o problema é que o código viola essa arquitetura em vários pontos, não que a arquitetura esteja errada.

Depois da fase de manutenção (Frentes 1–4, ver seção 15), surgiu uma **segunda disciplina/trabalho**: um relatório de **Soberania de Software (SSQM)**, avaliando o quanto o projeto está "preso" (lock-in) a fornecedores — principalmente Google/Firebase — e um **plano de migração para uma arquitetura própria/sem Firebase**, com um desenho experimental para medir o quanto LLMs conseguem executar essa migração (seção 16 e 17).

Linha do tempo reconstruída pelas datas dos documentos:

| Data | Marco |
|---|---|
| — | Projeto criado em disciplina de graduação (React + FastAPI + Firebase RTDB) |
| 2026-05-11 | Relatório de refatoração + PRD de refatoração + ADRs 0001–0005 (decisão: manutenção, não reengenharia) |
| 2026-05-24 | `docs/frentes-refatoracao.md` — decomposição em 4 frentes de trabalho |
| 2026-05-25 | Frente 4 concluída (branch `frente4-emanuel`, merge com `frente2-leo`) — 54 testes passando |
| 2026-06-08 | Relatório Final SSQM — SSQMScore 43,3% (Nível 3, "Dependência Moderada") |
| (atual) | `docs/plano-migracao-poshboard-llm.md` — plano de 2 semanas para migrar para fora do Firebase, medindo eficácia/eficiência de LLMs no processo |

---

## 3. Objetivos do produto

Da perspectiva de negócio/domínio (não técnica), o sistema existe para que um **programa de pós-graduação** (PPG) consiga:

1. Manter cadastro de **docentes** (permanentes, colaboradores, visitantes) e **discentes** (mestrado/doutorado).
2. Rastrear **linhas de pesquisa**, **projetos** e **pesquisas** (a relação orientador↔discente↔projeto↔linha).
3. Rastrear **veículos** de publicação (journals, conferências) e sua classificação (Qualis).
4. Coletar automaticamente a **produção científica** de cada docente/autor a partir de fontes acadêmicas públicas (OpenAlex, ORCID, Crossref, Semantic Scholar), sem depender de digitação manual.
5. Calcular **métricas bibliométricas** por autor: h-index, h5-index, i10-index, total de citações, coautores mais frequentes, tópicos/conceitos mais frequentes.
6. Exibir tudo isso em dashboards e relatórios visuais (gráficos de barra, linha, pizza, histograma).
7. (Meta, não implementada) Exportar relatórios em formato compatível com a **Plataforma Sucupira** (sistema oficial da CAPES de avaliação de PPGs no Brasil).

---

## 4. Stack tecnológica

| Camada | Tecnologia | Observação |
|---|---|---|
| Backend | Python 3.11+ (testado com 3.12) · FastAPI 0.115 · Uvicorn 0.30 | `functions/main.py` é o entrypoint |
| Validação | Pydantic v2 (2.9.2) + pydantic-settings 2.6.1 | só parte dos endpoints usa Pydantic de verdade (ver seção 8) |
| Banco de dados | **Firebase Realtime Database** (RTDB) | não é Firestore, apesar da documentação já descrever Firestore como meta (ADR 0001) |
| SDK de banco | `firebase-admin` 6.5.0 (síncrono) | sem suporte async nativo — motivo do ADR 0005 |
| HTTP client (backend→APIs externas) | `requests` 2.32.3 | síncrono |
| Frontend | React 19.1 + Vite 7.1 + React Router 7.9 | pasta `apresentacao/` |
| Gráficos | Chart.js 4.5 / react-chartjs-2 / Recharts 3.2 | duas libs de gráfico coexistindo |
| Auth | Firebase Auth | **stub no frontend** (`AuthProvider.jsx`), **não implementado no backend** — nenhuma rota valida ID Token |
| Hosting frontend | Firebase Hosting | `firebase.json`, publica pasta `public/` (não `apresentacao/dist`, ver drift na seção 16) |
| Hosting backend | Cloud Run (documentado) | não há `Dockerfile` no repositório atual — apenas mencionado em `docs/ARCHITECTURE.md` |
| Jobs agendados | Cloud Run Jobs + Cloud Scheduler (documentado) | pasta `functions/jobs/` **não existe** no código — só na documentação |
| CI/CD | GitHub Actions (`.github/workflows/`) | 2 workflows, ambos só de **deploy do Firebase Hosting** (merge/PR); não há workflow de testes/lint |
| Testes | pytest 8+ + httpx (`TestClient`) | 4 arquivos, 54 passed + 1 skipped (emulador) |
| Diagramas | `uml_packages.py` (script próprio) → gera `packages.puml` / `components.puml` (PlantUML) | |

---

## 5. Arquitetura

### 5.1 Visão geral (documentada, alvo)

```
┌──────────────────────────────────────────┐
│  Interface       api_routes/ + jobs/      │  Recebe requisições HTTP / cron
├──────────────────────────────────────────┤
│  Aplicação       services/ + workers/     │  Lógica de negócio
├──────────────────────────────────────────┤
│  Domínio         domain/                  │  Tipos, enums, schemas Pydantic
├──────────────────────────────────────────┤
│  Infraestrutura  repositories/ + ingest/  │  Acesso a banco e APIs externas
└──────────────────────────────────────────┘
```

**Regra de dependência:** cada camada só conhece a camada imediatamente abaixo. `api_routes` chama `services` ou `repositories`; nunca acessa o Firebase Admin SDK diretamente (regra violada em pontos específicos — ver seção 18/19).

### 5.2 Arquitetura real de hospedagem (AS-IS, segundo relatório SSQM)

```text
Usuário
  │
  ▼
Frontend React/Vite (apresentacao/)
  │                 \
  │                  \ fallback direto via REST
  ▼                   ▼
Backend FastAPI       Firebase RTDB
functions/main.py       ▲
  │                     │
  ▼                     │
Rotas, services,        │
repositories e ingest    │
  │                     │
  ▼                     │
Firebase Admin SDK ─────┘
  │
  └──► APIs externas de metadados acadêmicos
       OpenAlex, ORCID, Crossref, Semantic Scholar
```

### 5.3 Arquitetura alvo pós-migração (TO-BE, sem Firebase — ver seção 17)

```text
Usuário
  │
  ▼
Frontend React/Vite ──(somente HTTP/JSON)──┐
                                           ▼
                              API / BFF FastAPI
                                           │
                        ┌──────────────────┼───────────────────────┐
                        ▼                  ▼                        ▼
                 Application Services   Portas (interfaces)     Health/Métricas
                        │            ┌── RepositoryPort
                        │            ├── IngestionPort
                        │            └── AuthPort
                        ▼
        ┌───────────────┼─────────────────────────────────────────┐
        ▼               ▼                  ▼                        ▼
  Adaptador          Adaptador        Adaptadores ext.        Exportação/Backup
  PostgreSQL         Cache/Fila       OpenAlex/ORCID/         (JSON/CSV/dump)
  (SQLAlchemy)       (Redis+worker)   Crossref/S2 c/ cache
        │
   [Adaptador Firebase LEGADO — temporário, só p/ validação paralela]
```

Padrão de migração planejado: **Strangler Fig + Parallel-run** — o adaptador Firebase permanece atrás da mesma `RepositoryPort` enquanto o adaptador PostgreSQL é construído, permitindo leitura/escrita dupla e comparação de fidelidade antes de desativar o Firebase.

### 5.4 Handlers síncronos (dívida técnica intencional)

Todos os handlers HTTP são `def` síncronos, não `async def`. O FastAPI os executa em um thread pool interno. Isso é **decisão deliberada** (ADR 0005): o `firebase-admin` Python não tem cliente async, então forçar `async def` agora exigiria `run_in_executor` em toda chamada ao banco — mais complexo, sem ganho real. A decisão é migrar para `async def` **junto** com a troca de banco para Firestore/PostgreSQL (que têm clientes async nativos).

---

## 6. Estrutura de pastas completa

```
rpv/                              (raiz do repositório; projeto Firebase "poshbard")
├── functions/                    Backend Python
│   ├── main.py                   Entrypoint FastAPI: CORS, rotas soltas, registro de todos os routers
│   ├── api_routes/               Handlers HTTP por entidade
│   │   ├── docentes.py           CRUD com Pydantic (DocenteCreate/Out) + lru_cache
│   │   ├── discentes.py          CRUD com Pydantic (DiscenteCreate/Out) + lru_cache
│   │   ├── projetos.py           CRUD com Pydantic (ProjetoCreate/Out) + lru_cache
│   │   ├── linhas.py             CRUD com body: dict (sem Pydantic)
│   │   ├── veiculos.py           CRUD com body: dict (sem Pydantic)
│   │   ├── produtos.py           GET listar + GET /ranking (delega a services/produtos.py)
│   │   ├── pesquisas.py          CRUD de "Pesquisa" — ⚠️ NÃO registrado em main.py (órfão)
│   │   ├── processamento.py      POST /process/batch/{id} — ⚠️ NÃO registrado em main.py (órfão)
│   │   ├── autores.py            CRUD de autor canônico + /produtos + /metrics
│   │   ├── autores_flat.py       Geração da view desnormalizada autores_flat (generate/batch_generate)
│   │   ├── autores_generate.py   Gera /autores a partir de /openalex
│   │   ├── autores_links.py      Vincula autor (OpenAlex) ↔ docente cadastrado
│   │   ├── autores_merge.py      Consolida external/* em /autores (upsert por ORCID)
│   │   ├── harvest_authors.py    Harvester "tudo de uma vez": OpenAlex+ORCID+Crossref+S2+/autores
│   │   └── processamento_openalex.py  Processa último batch raw de /openalex/{id} → canonical
│   ├── ingest/                   Clientes HTTP para APIs externas
│   │   ├── openalex.py           ⚠️ NÃO registrado em main.py (órfão/superado)
│   │   ├── openalex_name.py      Busca/importa autor por nome (maior arquivo do pacote, 383 linhas)
│   │   ├── openalex_orcid.py     Ingestão via ORCID → OpenAlex
│   │   ├── openalex_ingest_only.py  Importa sem processar (só salva raw)
│   │   ├── orcid_api.py          Baixa profile ORCID puro
│   │   ├── crossref_api.py       Busca obras por nome de autor no Crossref
│   │   └── semanticscholar_api.py  Busca/importa autor no Semantic Scholar
│   ├── workers/                  Processamento em lote raw → canonical
│   │   ├── batch_processor.py    Processa um batch (usado por api_routes/processamento.py, órfão)
│   │   ├── openalex_mapper.py    Mapeia payload OpenAlex → formato canônico
│   │   ├── openalex_orcid_processor.py  Processa resultado de ingestão via ORCID
│   │   ├── resolvers.py          Resolve/casa autores entre fontes
│   │   └── upsert.py             Upsert genérico no RTDB
│   ├── services/                 Lógica de negócio (camada de Aplicação)
│   │   ├── analytics.py          h-index/h5-index/i10-index — puro, sem I/O (ver seção 10)
│   │   ├── produtos.py           Ranking de autores por nº de produtos
│   │   └── pesquisa.py           PesquisaService — ⚠️ não usado por nenhuma rota (ver seção 18)
│   ├── repositories/             Acesso a dados (BaseCRUD + especializações)
│   │   ├── base.py                BaseCRUD: create/list/get/update/delete genéricos sobre RTDB
│   │   ├── docente_crud.py, discente_crud.py, projeto_crud.py, linha_crud.py,
│   │   │   veiculo_crud.py, produto_crud.py, pesquisa_crud.py
│   │   └── validators.py
│   ├── domain/                   Tipos e schemas
│   │   ├── types.py               Enums: TipoDocente, StatusPesquisa
│   │   └── schemas.py             Pydantic: Docente/Discente/Projeto (Create/Out) — só estas 3 entidades
│   └── common/
│       └── dbref.py                Único ponto de acesso: ref(path) → db.reference(path), lazy init
├── config/
│   ├── settings.py                 pydantic-settings: PROJECT_ID, RTDB_URL, API_PORT, OPENALEX_MAILTO, GOOGLE_APPLICATION_CREDENTIALS
│   └── firebase_admin_init.py      init_firebase() — inicialização idempotente do Firebase Admin SDK
├── apresentacao/                 Frontend React (Vite) — ver seção 11
│   ├── src/                       App React real (rotas, páginas, componentes)
│   ├── public/                    Imagens estáticas (inclui fotos de integrantes do time)
│   ├── index.html                 <title>4GTAG</title> — nome do grupo/projeto acadêmico
│   ├── package.json, vite.config.js, eslint.config.js
│   └── components/, pages/, schemas/, services/   ⚠️ arquivos Python soltos, quase todos stub — ver seção 18
├── docs/                          Documentação do projeto (este arquivo incluso)
│   ├── ARCHITECTURE.md
│   ├── CLAUDE.MD
│   ├── brainstorming.md
│   ├── prd-refatoracao.md
│   ├── relatorio-refatoracao.md
│   ├── frentes-refatoracao.md
│   ├── frente 4.md
│   ├── plano-migracao-poshboard-llm.md
│   └── adr/0001..0005-*.md
├── relatorio-final-ssqm/          Relatório de soberania (Markdown, .bib e .tex) — ver seção 16
├── tests/                         pytest — ver seção 12
├── scripts/
│   ├── seed_rtdb.py
│   └── windows/backend.ps1, frontend.ps1   Scripts de bootstrap para Windows
├── .github/workflows/            Só deploy do Firebase Hosting (merge + PR preview)
├── firebase.json, .firebaserc, firestore.rules, firestore.indexes.json, storage.rules
├── requirements.txt, requirements-dev.txt, pytest.ini, conftest.py, setup.py
├── package.json                  Scripts-raiz que delegam para apresentacao/ (dev/build/lint/preview)
├── uml_packages.py                Gerador de diagramas PlantUML (packages.puml, components.puml)
├── ingest_varios.py, inspect.sh   Scripts utilitários na raiz
├── APRESENTACAO.md                Visão geral (documento "pitch" do projeto)
└── README.md                      Setup local (Windows/Linux/Docker), variáveis de ambiente, troubleshooting
```

---

## 7. Modelo de dados

### 7.1 Banco: Firebase Realtime Database (RTDB)

Estrutura em árvore JSON (documentação em `docs/ARCHITECTURE.md`):

```
/docentes/{id}          → perfil de docente (nome, tipo, orcid, lattes, scholar…)
/discentes/{id}         → perfil de discente (nome, status, orientador, datas…)
/linhas/{id}            → linha de pesquisa
/projetos/{id}          → projetos de pesquisa
/pesquisas/{id}         → vínculo orientador↔discente↔projeto↔linha (entidade "Pesquisa")
/veiculos/{id}          → journals / conferências
/produtos/{id}          → produções científicas
/autores/{id}           → registro canônico de autor
/autores_flat/{id}      → view desnormalizada por nome, com obras agregadas + métricas
/openalex/{id}/batches/ → snapshots BRUTOS do OpenAlex (imutáveis, histórico por timestamp)
/external/{fonte}/{id}/ → dados brutos de ORCID, Crossref, Semantic Scholar
/staging/               → dados intermediários antes do processamento
```

### 7.2 Modelo Raw + Canonical (ADR 0004)

Toda fonte externa (OpenAlex, ORCID, Crossref, Semantic Scholar) tem vocabulário próprio (`display_name` vs `author.name` vs `name`; `cited_by_count` vs `citationCount` etc.). Em vez de normalizar na hora da ingestão (perdendo o dado original) ou só guardar bruto (inutilizável direto), o sistema guarda **as duas camadas**:

- **Raw** — dado exatamente como veio da API, em `/openalex/{id}/batches/{timestamp}/` e `/external/{fonte}/{id}/`. Nunca alterado. Nunca lido pela interface/API pública.
- **Canonical** — dado normalizado e fundido de várias fontes, em `/autores_flat/{slug}` e `/produtos/{id}`. É o que a API HTTP serve.

Pipeline: `ingest/` coleta e grava raw → `workers/` processa e grava canonical → `api_routes/` serve canonical.

Vantagens documentadas: auditabilidade (rastrear origem/data de cada dado), reprocessamento sem re-chamar APIs externas se a lógica de normalização mudar, fusão de múltiplas fontes sobre o mesmo autor, resiliência a rate limits.

### 7.3 Enums de domínio (`functions/domain/types.py`)

```python
class StatusPesquisa(str, Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    QUALIFICADA  = "QUALIFICADA"
    DEFENDIDA    = "DEFENDIDA"
    ARQUIVADA    = "ARQUIVADA"

class TipoDocente(str, Enum):
    PERMANENTE   = "PERMANENTE"
    COLABORADOR  = "COLABORADOR"
    VISITANTE    = "VISITANTE"
```

### 7.4 Schemas Pydantic (`functions/domain/schemas.py`)

Existem apenas para **Docente**, **Discente** e **Projeto** (`*Create`/`*Out`), todas herdando de `APIModel` (permite campos extra, normaliza enums para string). `Linha`, `Veículo` e `Pesquisa` **não têm** schema Pydantic — os endpoints correspondentes aceitam `body: dict` sem validação.

Curiosidade: os campos aceitam tanto nomes em português (`nome`, `titulo`, `dataInicio`) quanto em inglês (`name`, `dataInicio`/`data_inicio`) — reflexo de o frontend e o backend terem evoluído com convenções de nomenclatura diferentes em momentos distintos.

### 7.5 Mapeamento planejado RTDB → PostgreSQL (plano de migração)

| Nó RTDB | Tabela PostgreSQL alvo | Observação |
|---|---|---|
| `/autores/{id}` | `authors(id, nome, orcid, …)` | chave do nó → PK |
| `/produtos/{id}` | `works(id, titulo, doi, ano, …)` | DOI único; índice por ano |
| relação autor↔produto | `author_work(author_id, work_id)` | tabela de junção M:N explícita |
| `/programas/{id}` | `programs(id, nome, …)` | entidade de programa de pós |
| metadados de coleta | `ingestion_runs(id, fonte, status, …)` | rastreio OpenAlex/ORCID/Crossref/S2 |

---

## 8. API — todos os endpoints

Entrypoint: `functions/main.py`. CORS configurado via env `CORS_ORIGINS` (lista separada por vírgula); sem essa variável, aceita apenas `localhost`/`127.0.0.1` em qualquer porta (regex).

### 8.1 Rotas soltas (definidas direto em `main.py`, sem router)

| Método | Caminho | Descrição |
|---|---|---|
| GET | `/` | `{"status": "API rodando 🚀"}` |
| GET | `/health` | `{"ok": true}` |
| GET | `/autores_flat` | proxy: todo o nó `autores_flat` |
| GET | `/autores_flat/{author_id}` | proxy: um autor da view flat |
| GET | `/autores/{author_id}/metrics` | agrega h-index/h5/i10/citações — delega para `services/analytics.py` |

### 8.2 CRUD de entidades cadastrais

| Prefixo | Pydantic? | Métodos |
|---|---|---|
| `/docentes` | ✅ `DocenteCreate`/`DocenteOut` | POST, GET (lista), GET `/{id}`, PATCH `/{id}`, DELETE `/{id}` |
| `/discentes` | ✅ `DiscenteCreate`/`DiscenteOut` | idem |
| `/projetos` | ✅ `ProjetoCreate`/`ProjetoOut` | idem |
| `/linhas` | ❌ `body: dict` | idem |
| `/veiculos` | ❌ `body: dict` | idem |
| `/pesquisas` | ❌ `body: dict` | idem — **⚠️ router existe mas não está registrado em `main.py` (inacessível via HTTP)** |

Todos os CRUDs seguem o padrão: `POST ""` + `POST "/"` (alias oculto do Swagger), `GET ""` + `GET "/"`, `GET "/{id}"`, `PATCH "/{id}"`, `DELETE "/{id}"` (204).

### 8.3 Produtos (produção científica)

| Método | Caminho | Descrição |
|---|---|---|
| GET | `/produtos` (+ alias `/produtos/`) | lista produtos |
| GET | `/produtos/ranking` | ranking de autores por nº de produções (delega a `services/produtos.py`) |

### 8.4 Autores (entidade canônica)

Router `autores_router`, montado com `prefix="/autores"`:

| Método | Caminho | Descrição |
|---|---|---|
| GET | `/autores/` | lista autores |
| POST | `/autores/` | cria autor |
| GET | `/autores/{id}` | obtém autor |
| PATCH | `/autores/{id}` | atualiza autor |
| DELETE | `/autores/{id}` | remove autor |
| GET | `/autores/{id}/produtos` | produções de um autor |
| GET | `/autores/{id}/metrics` | **⚠️ inacessível** — rota idêntica já registrada antes em `main.py` (ver seção 18), o FastAPI usa a primeira que casar |

Outros routers relacionados a autor, cada um com seu próprio conjunto de caminhos completos:

| Router | Caminhos |
|---|---|
| `autores_links` | `GET /autores/unlinked` · `POST /autores/_reconcile_all` · `POST /autores/{autor_id}/link_to_docente/{docente_id}` |
| `autores_generate` | `POST /autores/generate_from_openalex` |
| `autores_merge` | `POST /autores/merge_sources` (consolida `external/*` em `/autores`, upsert por ORCID) |
| `autores_flat` | `POST /autores_flat/generate` · `POST /autores_flat/batch_generate` |
| `harvest_authors` | `POST /harvest/batch` (harvester completo: OpenAlex + ORCID + Crossref + S2 + `/autores`) |

### 8.5 Ingestão de fontes externas

| Prefixo (definido em `main.py`) | Router (arquivo) | Caminhos |
|---|---|---|
| `/ingest/openalex-orcid` | `openalex_orcid.py` | `POST /ingest/openalex-orcid/orcid` |
| `/ingest/openalex-name` | `openalex_name.py` | `GET /author_by_name` · `GET /_debug_ping` · `POST /import_by_name` · `POST /import_by_author_id` · +1 endpoint de importação adicional |
| `/ingest/openalex` | `openalex_ingest_only.py` | `GET /author_by_name` (sem salvar) · `POST /by_name_ingest_only` |
| `/processamento/openalex` | `processamento_openalex.py` | `POST /{author_id}` — processa último batch raw → canonical |

Routers com prefixo **próprio** (definido no arquivo, montados sem prefixo extra em `main.py`):

| Router | Prefixo próprio | Caminhos |
|---|---|---|
| `orcid_api.py` | `/ingest/orcid` | `GET /ingest/orcid/{orcid}` |
| `crossref_api.py` | `/ingest/crossref` | `POST /ingest/crossref/works_by_author_name` |
| `semanticscholar_api.py` | `/ingest/semanticscholar` | `GET /author_search` · `POST /import_author` |

### 8.6 Documentação interativa

- Swagger UI: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`

---

## 9. Pipeline de ingestão acadêmica

Fontes externas integradas e seu papel:

| Fonte | O que fornece | Cliente |
|---|---|---|
| [OpenAlex](https://openalex.org) | Metadados de obras, autores, citações, conceitos/tópicos | `ingest/openalex_name.py`, `openalex_orcid.py`, `openalex_ingest_only.py` |
| [ORCID](https://orcid.org) | Identificador persistente de pesquisador; profile | `ingest/orcid_api.py` |
| [Crossref](https://www.crossref.org) | Metadados de publicações via DOI | `ingest/crossref_api.py` |
| [Semantic Scholar](https://www.semanticscholar.org) | Dados adicionais de citação e resumos | `ingest/semanticscholar_api.py` |

Fluxo típico de importação de um autor (`harvest_authors.py::/harvest/batch` orquestra tudo):

1. Busca autor por nome/ORCID em cada fonte.
2. Salva resposta bruta em `/openalex/{id}/batches/{ts}` ou `/external/{fonte}/{id}`.
3. `workers/openalex_mapper.py` / `openalex_orcid_processor.py` traduzem o payload bruto para o formato canônico.
4. `workers/upsert.py` grava/atualiza o registro canônico em `/autores` ou `/autores_flat`.
5. `workers/resolvers.py` tenta casar/deduplicar autores entre fontes diferentes (ex.: mesmo pesquisador achado via nome no OpenAlex e via ORCID).
6. `api_routes/autores_links.py` permite (manual ou automaticamente via `_reconcile_all`) vincular um autor "solto" (só existe por ter sido achado numa API externa) a um **docente** já cadastrado no sistema.

`OPENALEX_MAILTO` (env var opcional) é usado para entrar no "polite pool" da API OpenAlex (rate limit melhor para quem se identifica com e-mail).

---

## 10. Métricas bibliométricas (analytics)

`functions/services/analytics.py` — módulo **puro** (sem I/O, sem Firebase), o que o torna totalmente testável sem emulador/rede. Recebe o nó `autores_flat/{id}` já lido do banco.

Índices calculados:

- **h-index**: maior `h` tal que `h` publicações têm ≥ `h` citações cada.
- **i10-index**: nº de publicações com ≥ 10 citações (limiar configurável).
- **h5-index**: h-index restrito às publicações dos últimos 5 anos. **Decisão de projeto**: o "ano de referência" por padrão é o maior ano presente nas obras do próprio autor (determinístico, não depende do relógio do servidor — mantém os testes reprodutíveis), mas pode ser passado explicitamente para alinhar com "últimos 5 anos completos" ao estilo Google Scholar.

Saída de `compute_author_metrics()`: `author_id`, `name`, `publications_count`, `total_citations`, `h_index`, `h5_index`, `i10_index`, `first_year`, `last_year`, `top_concepts` (top 10), `top_coauthors` (top 10), `sample_publications` (até 10).

Histórico: essa lógica **vivia inteira dentro do handler** `main.py` (~100 linhas) até a Frente 4 da refatoração (2026-05-25), quando foi extraída para esta camada de serviço — h5-index e i10-index nem existiam antes; foram implementados durante essa extração.

---

## 11. Frontend (`apresentacao/`)

### 11.1 App React real

`apresentacao/src/App.jsx` define as rotas (React Router):

| Rota | Página |
|---|---|
| `/` | `Home` |
| `/login` | `Login` (stub de autenticação) |
| `/teacher` | `Teacher` — CRUD de docentes |
| `/student` | `Student` — CRUD de discentes |
| `/project` | `Project` — CRUD de projetos |
| `/production` | `Production` — CRUD/listagem de produções |
| `/vehicle` | `Vehicle` — CRUD de veículos |
| `/reports` | `Report` |
| `/relatorio-producao` | `RelatorioProducao` |
| `/qualis` | `Qualis` — tabela Qualis (ver observação abaixo) |

Componentes organizados por domínio (`components/teacher/`, `student/`, `project/`, `production/`, `vehicle/`, `qualis/`), mais componentes de UI genéricos (`components/ui/`: `BarChart`, `LineChart`, `PieChart`, `Histogram`, `AreaBadge`, `QualisBadge`, `SearchSelect`). Cada domínio tende a ter `*Card`, `*Form`, `*Header`, `*List` e, nas páginas mais novas (`pages/Teacher/`, `pages/Student/`, etc.), um `*Provider.jsx` (Context API) ao lado da página — indício de uma segunda geração de páginas (com Context) coexistindo com a primeira geração mais simples (arquivos `Teacher.jsx` na raiz de `pages/`, alguns com `.jsx.bak`/`.jsx.orig` ao lado, sinal de refatoração em andamento/incompleta).

**Página Qualis**: existe (`pages/Qualis/`), mas — conforme `APRESENTACAO.md` — ainda **não consome dados reais** de classificação de veículos; é um ponto de melhoria conhecido.

**Auth**: `components/auth/AuthProvider.jsx` é o único artefato de autenticação; é stub — infraestrutura preparada, mas as rotas da API não verificam nenhum token.

**Acesso a dados**: a página consome a API FastAPI via HTTP (`VITE_API_URL`), mas `services/firebaseClient.js` e a variável `VITE_RTDB_URL` indicam que **algumas telas ainda têm fallback de leitura direta ao RTDB**, pulando a API — é justamente o smell CLS-03 do relatório SSQM (seção 16).

### 11.2 Arquivos Python "soltos" dentro de `apresentacao/`

Dentro da mesma pasta do frontend React existem arquivos Python que **não pertencem ao app Vite/React** e não são consumidos por ele: `components/__init__.py`, `components/footer.py`, `components/header.py`, `pages/__init__.py`, `pages/index.py`, `schemas/pesquisa_schema.py`, `services/firebase.py`, `services/__init__.py`. Ver seção 18 — são majoritariamente stubs (`# TODO: implementar`) sem nenhuma função/classe definida, aparentemente resíduo de uma tentativa paralela (framework como Reflex, que usa a mesma convenção de pastas `components/`/`pages/`) que nunca foi concluída nem conectada a nada.

---

## 12. Testes

Suíte em `tests/` (raiz do projeto), framework `pytest` + `httpx` (`TestClient`). Infraestrutura: `conftest.py` (raiz — insere o projeto no `sys.path`, define `PROJECT_ID`/`RTDB_URL` fake para `config.settings` importar sem `.env`) e `pytest.ini` (`testpaths = tests`, silencia warnings de depreciação do Pydantic v1/`on_event`).

| Arquivo | Linhas | Cobre |
|---|---:|---|
| `tests/test_analytics.py` | 180 | h-index/i10/h5 com citações conhecidas, `extract_works`, `compute_author_metrics` completo, nó vazio, limite de `sample_publications` — **sem Firebase** |
| `tests/test_docentes.py` | 154 | Rotas via `TestClient` com CRUD fake injetado (`dependency_overrides`): 201 criar, 422 em `tipo` inválido, normalização de caixa, 404, 204; teste direto de `find_by_orcid` (garante que não lança `AttributeError`) |
| `tests/test_schemas.py` | 81 | Pydantic: rejeição de `TipoDocente`/`StatusPesquisa` inválidos, `tipo` vazio → `None`, `to_payload()` excluindo `None`/unset, `id` obrigatório em `*Out`, campo extra permitido |
| `tests/test_base_crud.py` | 201 | Ciclo `create/list/get/update/delete` de `BaseCRUD` contra um **RTDB fake em memória** (sempre roda) + teste real contra **emulador Firebase** (opt-in via `FIREBASE_DATABASE_EMULATOR_HOST`, skip por padrão) |

**Resultado registrado na última execução documentada:** `54 passed, 1 skipped` (o skip é o teste de emulador, por design).

Como rodar:

```bash
pip install -r requirements-dev.txt
pytest                          # suíte completa (sem credenciais/rede)
pytest tests/test_base_crud.py  # inclui o teste de emulador, se configurado
```

**Não há testes automatizados de frontend** (nenhum Vitest/Testing Library configurado, apesar de ser um ponto de melhoria listado em `APRESENTACAO.md`).

---

## 13. Configuração, segurança e deploy

### 13.1 Variáveis de ambiente (backend, `config/settings.py`)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `PROJECT_ID` | ✅ | ID do projeto Firebase/GCP (ex.: `poshbard`) |
| `RTDB_URL` | ✅ | URL do Realtime Database |
| `API_PORT` | opcional (default 8000) | porta do Uvicorn |
| `OPENALEX_MAILTO` | opcional | e-mail para polite pool do OpenAlex |
| `GOOGLE_APPLICATION_CREDENTIALS` | opcional | caminho do JSON de service account (ADC) |
| `CORS_ORIGINS` | opcional | lista de origens separadas por vírgula; sem ela, só localhost |

Frontend (`apresentacao/.env`): `VITE_API_URL` (default `http://127.0.0.1:8000`), `VITE_RTDB_URL` (fallback de leitura direta ao RTDB em algumas telas — ver seção 11).

### 13.2 Credenciais

Backend usa **Application Default Credentials** (`credentials.ApplicationDefault()`). Em dev local: `GOOGLE_APPLICATION_CREDENTIALS` apontando para JSON de service account, ou `gcloud auth application-default login`. Em produção (Cloud Run, documentado): service account vinculada ao serviço via ADC, sem JSON no container.

### 13.3 Deploy

- **Frontend**: Firebase Hosting, publicando a pasta `public/` conforme `firebase.json` — mas o README documenta build em `apresentacao/dist`, e o SSQM aponta esse descompasso como drift de configuração (seção 16, CLS-07).
- **Backend**: documentado para Cloud Run (`docker build` + `docker push` + `uvicorn functions.main:app --host 0.0.0.0 --port $PORT`), mas **não há `Dockerfile` no repositório atual**.
- **CI/CD**: `.github/workflows/firebase-hosting-merge.yml` (deploy em push para `main`) e `firebase-hosting-pull-request.yml` (preview em PR) — ambos só de **frontend**; usam `projectId: metaorganizer-project`, que **diverge** do `.firebaserc` (`poshbard`) — outro drift documentado no relatório SSQM.

### 13.4 Riscos de segurança conhecidos (históricos, endereçados na Frente 1)

- `service-account.json` chegou a ficar rastreado no git (removido/`.gitignore` ajustado na Frente 1; se ainda houver histórico exposto, a credencial precisa ser rotacionada no Firebase Console).
- CORS já não é mais hardcoded (era `localhost` fixo; hoje é via `CORS_ORIGINS`).

---

## 14. Decisões arquiteturais (ADRs)

Todas datadas de 2026-05-11, em `docs/adr/`:

| ADR | Decisão | Justificativa resumida |
|---|---|---|
| **0001** | Migrar de Firebase RTDB para **Firestore** | RTDB só indexa um campo por vez; buscas por ORCID hoje exigem full scan (`autores_merge.py`). Firestore continua no ecossistema Firebase (Auth/Hosting inalterados) e permite queries compostas. **Ainda não executado** — o código continua em RTDB. |
| **0002** | **Manutenção sem reengenharia** | Estrutura `functions/` + FastAPI já é funcional; problemas são de qualidade interna, não de arquitetura. Reengenharia teria alto risco de regressão sem ganho proporcional. |
| **0003** | **Cloud Run** em vez de Firebase Functions | Firebase Functions não sustenta processo contínuo (FastAPI/Uvicorn precisa disso); Cloud Run roda containers com processo contínuo e integra nativamente com GCP/ADC. |
| **0004** | Modelo de dados em duas camadas: **Raw e Canonical** | Auditabilidade, reprocessamento sem re-chamar APIs externas, fusão de múltiplas fontes sobre o mesmo autor. Ver seção 7.2. |
| **0005** | **Handlers síncronos** como dívida técnica conhecida (gatilho de revisão: junto com ADR 0001) | `firebase-admin` não tem cliente async; forçar `async def` agora exigiria `run_in_executor` em toda chamada, sem ganho real. Migrar para async junto da troca de banco, quando o cliente Firestore/Postgres async assíncrono estiver disponível. |

> Nota importante: **nenhum dos ADRs 0001 e 0003 foi executado ainda** no código atual — RTDB continua sendo o banco, e não há `Dockerfile`/config de Cloud Run no repositório. São decisões registradas, não implementadas. O plano da seção 17, inclusive, propõe pular Firestore e ir direto para **PostgreSQL** (mudança de rumo em relação ao ADR 0001 original — motivada pelo objetivo de soberania/saída completa do Firebase, não só resolver queries).

---

## 15. Histórico de refatoração (Frentes 1–4)

Depois do relatório de refatoração (2026-05-11), o trabalho foi dividido em 4 frentes (`docs/frentes-refatoracao.md`, 2026-05-24):

### Frente 1 — Infraestrutura e Segurança (independente, paralela)
Remover `service-account.json` do histórico git + rotacionar credencial; `.gitignore`; CORS via `CORS_ORIGINS`; documentar no README/ARCHITECTURE; remover arquivos de conflito de merge (`package_BACKUP_379.json` etc.).

### Frente 2 — Renomeação, Centralização e Bug Crítico (pré-requisito de 3 e 4)
- `commom/` → `common/` (typo) e `crud/` → `repositories/`, em commits únicos com todos os imports atualizados.
- Bug crítico corrigido: `DocenteCRUD.find_by_orcid` chamava `self._node()`, método **inexistente** em `BaseCRUD` (só existe `self.ref()`) → `AttributeError` garantido em produção. Corrigido para `self.ref()`.
- `_db()`, antes redefinida em 5+ arquivos (`autores_merge.py`, `autores_flat.py`, `ingest/openalex.py`, `workers/upsert.py`, `workers/resolvers.py` — este com 5 variantes!), centralizada em `common/dbref.py::ref()`.
- `TIPOS_VALIDOS` (set local duplicando os valores do enum) substituído pelo uso direto de `TipoDocente`.

### Frente 3 — Qualidade FastAPI
Criação de `domain/schemas.py` (Docente/Discente/Projeto); substituição de `body: dict` por esses modelos nos 3 endpoints; `response_model=` adicionado; padrão `_crud = None` global mutável substituído por `@lru_cache`; `HTTPException` consolidada no topo de cada arquivo; acesso direto ao Firebase removido de `produtos.py` (extraído para `services/`).

### Frente 4 — Camada de Serviços e Testes ✅ concluída em 2026-05-25
Detalhada em `docs/frente 4.md`. Extraiu ~90 linhas de lógica de métricas de `main.py` para `services/analytics.py` (implementando h5-index e i10-index, que não existiam antes); escreveu os 4 arquivos de teste da seção 12. Foi implementada primeiro contra a estrutura antiga (`crud/`, `commom/`) e depois **integrada via merge** com a branch `frente2-leo` (em vez de reimplementar a Frente 2) — o merge gerou 9 conflitos, resolvidos mantendo o código moderno (Frentes 3/4) sobre a estrutura nova (Frente 2). Resultado final da branch: Frentes 1+2+3+4 juntas, alinhadas com `ARCHITECTURE.md` e os ADRs.

Achados extras dessa sessão de trabalho, registrados em `docs/frente 4.md`:
- `.env.example` não existia (criado).
- `.env` versionado apontava `GOOGLE_APPLICATION_CREDENTIALS` para caminho Windows de outra máquina (`C:\Users\ResTIC16\...`) — quebra qualquer endpoint que toque o banco em máquina diferente.
- README não documentava testes (corrigido).

**Estado atual do código confirma que essas 4 frentes já foram aplicadas**: as pastas já são `repositories/`/`common/` (não `crud/`/`commom/`), `find_by_orcid` já usa `self.ref()`, `services/analytics.py` já tem a lógica completa, `domain/schemas.py` já existe com os 3 modelos.

---

## 16. Relatório de Soberania de Software (SSQM)

Localização: `relatorio-final-ssqm/` (`.md.md`, `.tex`, `.bib`). Avaliação datada de 2026-06-08, usando o **Software Sovereignty Quality Model (SSQM)** — mede o quanto o sistema está "preso" (lock-in) a fornecedores.

### 16.1 Resultado

| Índice | Valor | Leitura |
|---|---:|---|
| **SSQMScore** | 0,43 (43,3%) | **Nível 3 — Dependência Moderada** (escala: 0–20% crítica, 21–40% alta, 41–60% moderada, 61–80% soberania parcial, 81–100% soberania alta) |
| IDC (dependência crítica) | 0,53 | puxado por Firebase RTDB, Admin SDK, ADC, OpenAlex |
| IP (portabilidade) | 0,58 | stack de aplicação é portável; dados/Firebase reduzem a mobilidade |
| CLSn (smells normalizados) | 0,67 | destaque para banco, SDK vazado e bypass do frontend |
| IDAN (dependência arquitetural em nuvem) | 0,55 | fórmula: `(IDC + CLSn + (1−IP) + (1−SSQMScore)) / 4` |

Pontuação por dimensão (0–10 cada, total 39/90):

| Dimensão | Nota | Leitura |
|---|---:|---|
| ST — Soberania Tecnológica | 3/10 | tecnologias abertas no stack, mas persistência/operação dependem de Firebase |
| SO — Soberania Operacional | 1/10 | sem contingência para indisponibilidade do provedor |
| SD — Soberania de Dados | 2/10 | sem rotina documentada de exportação/backup/migração independente |
| SA — Soberania Arquitetural | 4/10 | há `repositories`/`dbref`, mas ainda há chamadas Firebase espalhadas e frontend acessando RTDB direto |
| SI — Soberania de IA | 10/10 | sistema não depende de IA externa em produção hoje |
| SDV — Soberania de Desenvolvimento | 8/10 | build local bem documentado; CI/CD ainda depende de GitHub/Firebase |
| SK — Soberania de Conhecimento | 6/10 | boa documentação, mas com referências desatualizadas/incompletas |
| SE — Soberania de Ecossistema | 3/10 | concentração Google/Firebase relevante |
| SS — Soberania Estratégica | 2/10 | faltava plano formal de migração antes deste relatório |

### 16.2 Lock-in smells identificados

| ID | Smell | Severidade |
|---|---|---|
| CLS-01 | Firebase RTDB como persistência principal | Crítica |
| CLS-02 | SDK Firebase (`firebase_admin.db`) vazando para várias camadas (main.py, services/pesquisa.py, scripts, repositórios) | Alta |
| CLS-03 | Frontend com fallback direto para RTDB (`VITE_RTDB_URL`, `*.firebaseio.com/*.json`) | Alta |
| CLS-04 | Credenciais operacionais vinculadas a Google ADC/service account | Alta |
| CLS-05 | Hosting/deploy acoplados ao Firebase | Moderada |
| CLS-06 | Ingestão acadêmica sem cache/snapshot robusto (dependência de OpenAlex/ORCID/Crossref/S2) | Moderada |
| CLS-07 | **Drift de configuração**: `.firebaserc` usa `poshbard`, workflows usam `metaorganizer-project`, README cita diretório de hosting diferente do `firebase.json` | Moderada |
| CLS-08 | **Documentação arquitetural divergente do código**: `ARCHITECTURE.md` descreve Firestore/Auth/Jobs como já operacionais; código ainda usa RTDB e não tem `functions/jobs/` | Moderada |
| CLS-09 | Dependência potencial do Firebase JS SDK no frontend (`package.json` ainda declara `firebase`, embora `firebaseClient.js` esteja parcialmente stubado) | Baixa (atual) |

### 16.3 Inventário de dependências (22 itens, `DEP-01`–`DEP-22`)

Resumo por grupo:

| Grupo | Qtde | Risco |
|---|---:|---|
| Google/Firebase (RTDB, Admin SDK, ADC, Hosting, JS SDK) | 5 | Alto — concentra dados, credenciais e publicação |
| APIs acadêmicas externas (OpenAlex, ORCID, Crossref, S2) | 4 | Médio — afeta ingestão/atualização |
| npm/React (React, Vite, Router, gráficos, lint, npm) | 7 | Baixo/médio, boa substituibilidade |
| Python/PyPI (FastAPI, Uvicorn, Pydantic, dotenv, requests, PyPI) | 6 | Baixo/médio, tecnologias abertas |
| GitHub/Microsoft (GitHub Actions) | 1 | Baixo/médio, acoplado aos workflows atuais |

### 16.4 Roadmap de migração recomendado (0–36 meses)

| Horizonte | Foco | Esforço estimado |
|---|---|---:|
| 0–6 meses | Remover fallback do frontend ao RTDB; centralizar 100% do acesso Firebase em adapters; exportação JSON/CSV; corrigir drift de config; testes; cache nas ingestões externas | 184–352 h |
| 6–18 meses | Adaptador PostgreSQL; script de migração RTDB→PG com validação/rollback; containerização; separar ingestão em jobs/fila; CI/CD portável; estratégia de auth própria | 392–764 h |
| 18–36 meses | Operar sem Firebase (próprio/híbrido); backup/restore automatizado testado; cache/mirror de metadados acadêmicos; observabilidade própria; revisão SSQM semestral | 376–832 h |

**Total estimado:** 952–1.948 horas.

### 16.5 Conclusão do relatório

> "O Poshboard não está preso por toda a sua tecnologia: linguagem, framework backend, frontend e bibliotecas principais são majoritariamente abertas e substituíveis. O problema central de soberania está na **concentração de dados, credenciais e operação em Firebase/Google**, somada a acessos diretos ao RTDB no backend e no frontend."

---

## 17. Plano de migração + experimento com LLMs

Documento: `docs/plano-migracao-poshboard-llm.md`. Usa o relatório SSQM (seção 16) como baseline e propõe simultaneamente (a) um plano de migração real para **sair do Firebase** e (b) um **desenho experimental** para medir quão eficazes/eficientes LLMs são para executar essa migração. Mudança-alvo: **LONG-01** ("Operar versão sem Firebase em ambiente próprio ou híbrido") do roadmap SSQM, adiantada para uma janela de **2 semanas**.

### 17.1 Alvo de arquitetura

Self-hosted com Docker Compose (PostgreSQL + Redis + app + proxy reverso), com variação híbrida documentada (imagem em registry neutro + deploy em Cloud Run/Postgres gerenciado) para não recriar lock-in.

### 17.2 Work Packages (WP-1 a WP-10)

| WP | Objetivo | Baseline (relatório) |
|---|---|---:|
| WP-1 | Mapa RTDB → schema relacional | 16–32 h |
| WP-2 | Portas de repositório + adaptador PostgreSQL (SQLAlchemy/Alembic) | 120–220 h |
| WP-3 | ETL RTDB→PostgreSQL com validação de paridade e rollback | 80–160 h |
| WP-4 | Centralizar 100% do acesso Firebase em adaptador único | 40–80 h |
| WP-5 | Desacoplar frontend do RTDB (só API) | 24–40 h + 8–16 h |
| WP-6 | Identidade/segredos sem Google ADC | 40–120 h |
| WP-7 | Containerização própria/híbrida (Docker Compose) | 40–80 h |
| WP-8 | Ingestão resiliente (cache/fila/retries) | 80–160 h + 32–64 h |
| WP-9 | CI/CD portável + observabilidade + backup | 24–48 h + 80–160 h |
| WP-10 | Desligar Firebase e re-pontuar SSQM | 160–320 h |

Padrão de migração: **Strangler + Parallel-run** (adaptador Firebase permanece atrás da mesma `RepositoryPort` até o adaptador PostgreSQL ser validado por paridade de dados).

### 17.3 Desenho experimental

- **Unidade experimental:** cada WP.
- **Condições:** C0 (baseline humano = estimativa do relatório), C1 (LLM assistida por humano), C2 (LLM autônoma/agente), C3 (modelo B, para comparar entre LLMs).
- **Métricas de eficácia:** taxa de testes verdes (meta ≥95%), fidelidade de dados RTDB×PG (meta ≥99,9%), acoplamento residual (`grep` por `firebase_admin.db`/`firebaseio.com`/`VITE_RTDB_URL`, meta 0), conformidade arquitetural, build/deploy, segurança (`gitleaks`, `pip-audit`), % de critérios de aceite sem correção humana.
- **Métricas de eficiência:** tempo real por WP vs. baseline (fator de aceleração), custo de tokens/API, iterações até verde, % de intervenção humana (via `git blame`), taxa de retrabalho.
- **Métricas de processo:** alucinações (APIs/arquivos inventados), aderência à instrução, reprodutibilidade (variância entre execuções repetidas), nível de autonomia (escala 0–4, Anexo C do plano).
- **Métrica-âncora:** *delta* nos índices SSQM antes×depois — meta pós-migração: SSQMScore ≥0,70 (de 0,43), IDAN ≤0,30 (de 0,55), IDC ≤0,30 (de 0,53), IP ≥0,80 (de 0,58), CLSn ≤0,20 (de 0,66).

### 17.4 Cronograma de 2 semanas

- **Semana 1** (preparação, sem LLM executando migração): congelar repo + export RTDB; escrever suíte de testes "golden"; definir rubrica de re-score SSQM e script de validação de fidelidade; montar planilha/instrumentação; congelar enunciados dos WPs.
- **Semana 2** (execução + coleta): dias 6–7 WP-1/2/3/4 (schema+adapter+ETL+centralização); dia 8 WP-5/7 (frontend só-API + containerização); dia 9 WP-6/8/9 (segredos+ingestão+CI/CD); dia 10 WP-10 (desligar Firebase + re-score) + análise final.

### 17.5 Riscos do experimento

Dados sensíveis reais no RTDB (mitigação: export anonimizado/amostral); LLM "passar nos testes" sem migrar de fato (mitigação: combinar testes + métrica de acoplamento + fidelidade + revisão humana); escopo grande para 2 semanas (mitigação: medir por WP, extrapolar); variância entre execuções (mitigação: replicar ≥2×); vazamento de segredos pela LLM (mitigação: scanner obrigatório); otimização para a métrica (mitigação: rubrica congelada antes da execução).

> **Nota**: este é um **plano**, ainda não um relato de execução — não há, no repositório atual, evidência de que a migração para PostgreSQL/Docker Compose já tenha começado (RTDB continua sendo o banco em uso, ver seções 5, 7 e 14).

---

## 18. Achados adicionais — código morto e duplicações não documentadas

Durante a leitura direta do código-fonte atual (não estava registrado em nenhum documento existente), foram encontrados os seguintes pontos:

1. **Rota `/autores/{id}/metrics` duplicada e parcialmente morta.** `main.py` define `GET /autores/{author_id}/metrics` diretamente (linha ~96), e o router `api_routes/autores.py` define outra rota idêntica em caminho (`GET /{id}/metrics`, montada sob `prefix="/autores"`). O FastAPI resolve pela ordem de registro — como a rota de `main.py` é declarada **antes** do `include_router(autores_router, ...)`, a versão de `api_routes/autores.py` nunca é alcançada. Trata-se de código morto por sombreamento de rota.

2. **`functions/api_routes/pesquisas.py` (router de CRUD de "Pesquisa") nunca é registrado em `main.py`.** O arquivo existe, importa `PesquisaCRUD`, define rotas completas (`POST/GET/PATCH/DELETE`), mas não há nenhum `app.include_router(pesquisas_router, ...)` — a entidade "Pesquisa" (o vínculo orientador↔discente↔projeto↔linha, central na ideia original do produto) **não é acessível via HTTP hoje**, apesar de o código para isso já existir.

3. **`functions/api_routes/processamento.py` (prefixo `/process`, `POST /process/batch/{id}`) também nunca é registrado em `main.py`.** É fácil confundir com `processamento_openalex.py`, que é o único efetivamente montado (em `/processamento/openalex`).

4. **`functions/ingest/openalex.py` (`POST /ingest/openalex/works`, com prefixo próprio `/ingest/openalex`) também não é importado em `main.py`.** Foi aparentemente superado por `openalex_ingest_only.py`, que é montado no mesmo prefixo (`/ingest/openalex`) via `main.py`. Ambos os arquivos reivindicam o mesmo espaço de URL; apenas um está de fato ativo.

5. **Duas implementações concorrentes da lógica de "Pesquisa".** `functions/services/pesquisa.py::PesquisaService` acessa `firebase_admin.db` diretamente (viola a regra de camadas — é exatamente o smell CLS-02 do relatório SSQM) e contém regra de negócio real (só permite orientador do tipo `PERMANENTE`), mas **não é usado por nenhum router** — nem mesmo pelo `pesquisas.py` órfão do item 2, que usa `PesquisaCRUD` (repositório genérico, sem a validação de orientador) em vez do `PesquisaService`. Ou seja: a única regra de negócio que valida "orientador precisa ser docente permanente" existe no código, mas está desconectada de qualquer rota.

6. **Arquivos Python soltos dentro de `apresentacao/` (pasta do frontend Vite/React) são, em sua maioria, stubs vazios e não pertencem ao app React nem ao backend FastAPI**: `apresentacao/pages/index.py` e `apresentacao/services/firebase.py` contêm literalmente só `# TODO: implementar`; `apresentacao/components/footer.py`, `header.py` e `pages/__init__.py`/`components/__init__.py` não definem nenhuma função ou classe. A única exceção com conteúdo real é `apresentacao/schemas/pesquisa_schema.py`, que define `PesquisaIn`/`PesquisaOut`/`PesquisaList` em Pydantic — um **terceiro** modelo de dados para "Pesquisa" (além do `PesquisaCRUD` do item 2 e do `PesquisaService` do item 5), fora do lugar arquitetural esperado (`functions/domain/`) e não referenciado por nada.

7. **Duplicação de libs de gráfico no frontend.** `package.json` declara tanto `chart.js`/`react-chartjs-2` quanto `recharts` — duas bibliotecas de visualização diferentes coexistindo, sem que a documentação explique quando usar cada uma. (`components/ui/BarChart.jsx`, `LineChart.jsx`, `PieChart.jsx`, `Histogram.jsx` usam uma delas — não verificado exaustivamente qual.)

8. **Duas gerações de páginas no frontend coexistindo.** Para várias entidades há tanto `pages/Teacher.jsx` (arquivo único) quanto `pages/Teacher/Teacher.jsx` + `pages/Teacher/TeacherProvider.jsx` (pasta com Context Provider) — mesmo padrão para Student, Project, Vehicle, Production. Só `App.jsx` importa de `./pages/Teacher` (resolve para o arquivo, não a pasta, dependendo da configuração do bundler) — indício de refatoração incremental para Context API ainda não finalizada/limpa. Há também `App.jsx.orig`, `Home.jsx.bak` e `package-lock.json.orig`/`package_BACKUP_379.json`-style residuais de merges antigos (parte já tratada na Frente 1, mas vale confirmar se `App.jsx.orig` e `Home.jsx.bak` ainda estão rastreados).

Nenhum desses 8 pontos está registrado em `docs/relatorio-refatoracao.md`, `docs/frentes-refatoracao.md`, `docs/frente 4.md` ou no relatório SSQM — são candidatos a uma futura "Frente 5" de limpeza.

---

## 19. Dívida técnica e pontos de melhoria conhecidos

Consolidado de `APRESENTACAO.md` + achados da seção 18:

### Funcionalidade
- Autenticação real (stub existe no frontend; API não valida ID Token).
- Painel de Qualis não consome dados reais de classificação de veículos.
- Relatórios exportáveis (PDF/CSV) e exportação para Sucupira.
- Busca, paginação e filtros por período nas listagens.
- Notificações ao coordenador (novas produções, mudanças de métrica).
- Entidade "Pesquisa" inacessível via API (achado 18.2/18.3).
- Agente de IA para scraping de Lattes (item da ideia original, nunca implementado).

### Técnico / arquitetural
- Migração RTDB → Firestore (ADR 0001) ou direto para PostgreSQL (plano da seção 17) — ainda não iniciada no código.
- Handlers assíncronos (ADR 0005), amarrado à migração de banco.
- Frontend sem TypeScript.
- Sem testes automatizados de frontend (Vitest + Testing Library seria a escolha natural com Vite).
- Sem pipeline de CI rodando `pytest`/`eslint` (workflows atuais só fazem deploy).
- Ingestão não idempotente — pipeline pode duplicar dados se executado 2x para o mesmo autor.
- Drift de configuração: `.firebaserc` (`poshbard`) vs. workflows (`metaorganizer-project`) vs. `firebase.json` (`public/`) vs. README (`apresentacao/dist`).
- Documentação (`ARCHITECTURE.md`) descreve Firestore/Cloud Run/Jobs como se já estivessem operacionais — código ainda usa RTDB, sem `Dockerfile` nem `functions/jobs/`.
- Código morto/órfão listado na seção 18.

### UX / Design
- Responsividade mobile (layout desktop-first).
- Dark mode.
- Internacionalização (sistema 100% em português).

---

## 20. Glossário

| Termo | Significado no sistema |
|---|---|
| Docente | Professor permanente, colaborador ou visitante do programa |
| Discente | Aluno de pós-graduação (mestrado/doutorado) |
| Pesquisa | Vínculo entre orientador (docente permanente), discente, projeto e linha de pesquisa, com status (`EM_ANDAMENTO`, `QUALIFICADA`, `DEFENDIDA`, `ARQUIVADA`) |
| Produto | Produção científica (artigo, livro, patente…) |
| Veículo | Onde o produto foi publicado (journal, conferência) |
| Linha | Linha de pesquisa do programa |
| Autor (canônico) | Registro em `/autores`, resultado da fusão/normalização de dados vindos de OpenAlex/ORCID/etc.; pode ou não estar vinculado a um Docente cadastrado |
| Raw / Canonical | Camadas de armazenamento — dado bruto de API externa vs. dado normalizado pronto para consumo (ADR 0004) |
| h-index | Maior *h* tal que *h* obras têm ≥ *h* citações |
| h5-index | h-index considerando apenas os últimos 5 anos |
| i10-index | Número de obras com ≥ 10 citações |
| Harvest | Processo de coleta/ingestão automática de dados acadêmicos de fontes externas |
| SSQM | Software Sovereignty Quality Model — framework usado para medir lock-in/soberania tecnológica (seção 16) |
| Lock-in smell (CLS) | Padrão de código/config que indica dependência problemática de um fornecedor específico |
| Strangler + Parallel-run | Padrão de migração: novo adaptador convive com o legado até paridade validada, só então o legado é desligado |
| LONG-01 | Item do roadmap SSQM: "operar versão sem Firebase em ambiente próprio ou híbrido" — mudança-alvo do plano da seção 17 |
| Sucupira | Plataforma oficial da CAPES (Brasil) de avaliação de programas de pós-graduação — destino de exportação de relatórios, ainda não implementado |

---

*Gerado por leitura completa do repositório em 2026-07-06. Documentos-fonte: todos os arquivos em `docs/`, `relatorio-final-ssqm/`, `README.md`, `APRESENTACAO.md`, e inspeção direta de `functions/`, `config/`, `apresentacao/`, `tests/`, `.github/workflows/`, `firebase.json`, `.firebaserc`, `package.json` (raiz e frontend).*
