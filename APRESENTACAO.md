# Poshboard — Visão Geral do Projeto

> Dashboard de acompanhamento de produção acadêmica para programas de pós-graduação.

---

## O que o sistema faz

O **Poshboard** centraliza e exibe informações de um programa de pós-graduação: docentes, discentes, projetos, veículos de publicação e a produção científica de cada pesquisador. Ele se conecta a APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar) para coletar, normalizar e exibir métricas como h-index, i10-index e h5-index de cada autor cadastrado.

Fluxo principal:

```
APIs Externas ──► Ingestão ──► Banco (Firebase) ──► API REST ──► Frontend React
(OpenAlex, ORCID,            (raw → canônico)     (FastAPI)     (dashboard)
 Crossref, SemanticScholar)
```

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Validação de dados | Pydantic v2 |
| Banco de dados | Firebase Realtime Database |
| Frontend | React 19 + Vite + React Router |
| Gráficos | Chart.js / Recharts |
| Autenticação | Firebase Auth (stub; infra preparada) |
| Hospedagem frontend | Firebase Hosting |
| Hospedagem backend | Cloud Run (Google Cloud) |
| Jobs agendados | Cloud Run Jobs + Cloud Scheduler |
| Testes | pytest + httpx |

---

## Arquitetura

O backend segue uma arquitetura em camadas bem definida:

```
┌──────────────────────────────────────────┐
│  Interface       api_routes/ + jobs/      │  Recebe requisições HTTP
├──────────────────────────────────────────┤
│  Aplicação       services/ + workers/    │  Lógica de negócio
├──────────────────────────────────────────┤
│  Domínio         domain/                 │  Tipos, enums, schemas
├──────────────────────────────────────────┤
│  Infraestrutura  repositories/ + ingest/ │  Acesso a banco e APIs externas
└──────────────────────────────────────────┘
```

### Estrutura de pastas

```
poshboard-main/
├── functions/
│   ├── main.py                  # Ponto de entrada FastAPI
│   ├── api_routes/              # Handlers HTTP (docentes, discentes, projetos…)
│   ├── services/                # Lógica de negócio (analytics, produtos)
│   ├── repositories/            # CRUD sobre o Firebase (BaseCRUD + especializações)
│   ├── domain/                  # Tipos Pydantic e enums
│   ├── ingest/                  # Clientes para APIs externas
│   └── workers/                 # Transformação raw → canônico
├── apresentacao/                # Frontend React (Vite)
│   ├── src/pages/               # Páginas (Home, Teacher, Student, Production…)
│   └── src/components/          # Componentes reutilizáveis
├── config/                      # Settings (Pydantic Settings) e init Firebase
├── tests/                       # Suite de testes
└── docs/
    ├── ARCHITECTURE.md
    └── adr/                     # 5 Architecture Decision Records
```

### Modelo de dados (Firebase Realtime Database)

```
/docentes/{id}          → perfil de docente (nome, tipo, orcid, lattes…)
/discentes/{id}         → perfil de discente
/projetos/{id}          → projetos de pesquisa
/veiculos/{id}          → journals / conferências
/produtos/{id}          → produções científicas
/autores/{id}           → registro canônico de autor
/autores_flat/{id}      → visão desnormalizada com obras agregadas
/openalex/{id}/batches/ → snapshots brutos do OpenAlex (imutáveis)
/staging/               → dados intermediários antes do processamento
```

---

## Principais endpoints da API

```
GET  /health                        # Status do serviço
GET  /autores/{id}/metrics          # h-index, h5-index, i10-index
GET  /docentes                      # Lista docentes
POST /docentes                      # Cadastra docente
POST /ingest/openalex-orcid/harvest # Coleta dados do autor via ORCID
POST /autores_flat/generate         # Gera visão desnormalizada
POST /processamento/openalex        # Processa dados brutos → canônico
```

---

## Testes

Existem 4 módulos de teste:

| Arquivo | O que cobre |
|---------|------------|
| `tests/test_docentes.py` | Rotas HTTP com CRUD fake em memória |
| `tests/test_analytics.py` | Cálculo de h-index, i10-index, h5-index |
| `tests/test_schemas.py` | Validação de schemas Pydantic |
| `tests/test_base_crud.py` | Integração com emulador do Firebase |

Para rodar:

```bash
pytest                          # testes unitários
pytest tests/test_base_crud.py  # requer Firebase Emulator
```

---

## Como rodar localmente

### Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # preencher PROJECT_ID, RTDB_URL e credenciais
uvicorn functions.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd apresentacao
npm install
npm run dev                     # http://localhost:5173
```

---

## Decisões de arquitetura relevantes (ADRs)

| ADR | Decisão |
|-----|---------|
| ADR 0001 | Migrar do Firebase RTDB para **Firestore** (melhor escala e suporte a async) |
| ADR 0003 | Usar **Cloud Run** em vez de Firebase Functions (FastAPI precisa de processo contínuo) |
| ADR 0005 | Handlers devem se tornar `async def` após migração para Firestore |

Os ADRs estão em `docs/adr/` e documentam o raciocínio por trás de cada escolha.

---

## Pontos de melhoria — o que a turma pode explorar

### Funcionalidade

- [ ] **Autenticação real**: o frontend tem o stub do Firebase Auth; falta proteger as rotas da API com verificação de ID Token.
- [ ] **Painel de Qualis**: a página `/qualis` existe mas ainda não consome dados reais de classificação de veículos.
- [ ] **Relatórios exportáveis**: gerar PDF/CSV dos relatórios de produção.
- [ ] **Busca e filtros**: as listagens não têm paginação, busca textual nem filtros por período.
- [ ] **Notificações**: avisar o coordenador quando novas produções forem ingeridas ou quando métricas mudarem significativamente.

### Técnico / Dívida arquitetural

- [ ] **Migração RTDB → Firestore** (ADR 0001): o banco atual (Realtime Database) é adequado para protótipos, mas Firestore oferece queries mais ricas, melhor suporte a async e regras de segurança granulares.
- [ ] **Handlers assíncronos** (ADR 0005): os handlers são `def` síncronos executados em thread pool; migrar para `async def` após adotar Firestore.
- [ ] **Frontend sem TypeScript**: o projeto usa JSX puro. Adicionar TypeScript melhoraria a segurança de tipos e a autocompletação.
- [ ] **Cobertura de testes do frontend**: não há testes automatizados para os componentes React (Vitest + Testing Library seria a escolha natural com Vite).
- [ ] **CI/CD**: não há pipeline de integração contínua configurado. Adicionar GitHub Actions rodando `pytest` e `eslint` em cada PR.
- [ ] **Tratamento de erros no frontend**: muitas páginas não tratam o caso de API indisponível; adicionar estados de erro e loading consistentes.
- [ ] **Ingestão idempotente**: o pipeline de ingestão pode gravar duplicatas se executado mais de uma vez para o mesmo autor; adicionar verificação de deduplicação.
- [ ] **Variáveis de ambiente no frontend**: credenciais do Firebase no cliente estão removidas por segurança — criar processo de injeção via CI para o build de produção.

### UX / Design

- [ ] Responsividade mobile (o layout atual é desktop-first).
- [ ] Dark mode.
- [ ] Internacionalização (i18n): o sistema está em português, mas a estrutura de páginas facilita adicionar suporte a outros idiomas.

---

## Referências externas utilizadas

| Serviço | O que fornece |
|---------|--------------|
| [OpenAlex](https://openalex.org) | Metadados de obras, autores, citações |
| [ORCID](https://orcid.org) | Identificador persistente de pesquisadores |
| [Crossref](https://www.crossref.org) | Metadados de publicações via DOI |
| [Semantic Scholar](https://www.semanticscholar.org) | Dados adicionais de citação e resumos |

---

## Glossário rápido

| Termo | Significado no sistema |
|-------|----------------------|
| Docente | Professor permanente, colaborador ou visitante do programa |
| Discente | Aluno de pós-graduação (mestrado/doutorado) |
| Produto | Produção científica (artigo, livro, patente…) |
| Veículo | Onde o produto foi publicado (journal, conferência) |
| Linha | Linha de pesquisa do programa |
| h-index | Métrica de impacto: maior *h* tal que *h* obras têm ≥ *h* citações |
| h5-index | h-index considerando apenas os últimos 5 anos |
| i10-index | Número de obras com ≥ 10 citações |
