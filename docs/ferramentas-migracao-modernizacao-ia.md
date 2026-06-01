# Ferramentas de Migração e Modernização com IA — Análise para o Poshboard

**Data:** 2026-06-01  
**Projeto:** Poshboard (RPV) — Sistema de gestão de pós-graduação  
**Referências internas:** `docs/ARCHITECTURE.md`, ADR 0001–0005, `docs/frentes-refatoracao.md`, `docs/prd-refatoracao.md`

---

## 1. Resumo executivo

O **Poshboard** é um monorepo com backend **FastAPI + Python** e frontend **React + Vite**, atualmente sobre **Firebase Realtime Database (RTDB)**. O projeto já possui um programa de refatoração bem documentado (quatro frentes, cinco ADRs) e está em **manutenção dirigida**, não em reengenharia (ADR 0002).

Este documento analisa o estado atual do repositório e pesquisa **ferramentas de migração/modernização**, com foco em soluções que utilizam **IA para transpilação** (conversão de código de uma forma para outra). A conclusão central é que o Poshboard se beneficia de uma **estratégia híbrida**:

| Abordagem | Papel | Exemplos |
|-----------|-------|----------|
| **Determinística** | Tarefas repetitivas, previsíveis, em massa | `bump-pydantic`, OpenRewrite (JS/TS), receitas de lint |
| **Assistida por IA** | Lógica de negócio, refatorações contextuais, migrações sem receita pronta | Cursor, GitHub Copilot, Claude Code |
| **Agentes especializados** | Migrações grandes entre linguagens ou plataformas | AWS Transform, AAMF, EltegraAI |

Para o Poshboard, a maior parte do trabalho **não é transpilação entre linguagens**, e sim **modernização dentro do mesmo stack** (RTDB → Firestore, Pydantic v1 → v2, sync → async, consolidação de camadas). Ferramentas determinísticas cobrem ~70% desse esforço; IA acelera o restante quando guiada pelos ADRs e pelas frentes de refatoração já definidas.

---

## 2. Análise do projeto

### 2.1 Propósito e domínio

Conforme `docs/CLAUDE.MD`, o sistema:

1. Gerencia professores, programas de pesquisa, projetos e bolsas.
2. Atualiza dados acadêmicos (publicações) via APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar) e, no futuro, agentes de IA (agno) para currículo Lattes.
3. Gera gráficos e relatórios exportáveis para plataformas como Sucupira.

### 2.2 Stack tecnológico

| Camada | Tecnologia | Versão (aprox.) |
|--------|-----------|-----------------|
| Backend | Python, FastAPI, Uvicorn | 3.11+, FastAPI 0.115 |
| Validação | Pydantic + pydantic-settings | 2.9.2 |
| Banco (atual) | Firebase RTDB | firebase-admin 6.5 |
| Banco (planejado) | Firestore | ADR 0001 |
| Frontend | React, Vite, React Router | React 19, Vite 7 |
| Gráficos | Chart.js + react-chartjs-2 | — |
| Testes | pytest + httpx | 54 passed, 1 skipped |
| Deploy (alvo) | Cloud Run + Firebase Hosting | ADR 0003 |

### 2.3 Arquitetura

```
[Interface]     api_routes/ + jobs/ (planejado)
      ↓
[Application]   services/ + workers/
      ↓
[Domain]        domain/ (types, schemas)
      ↓
[Infrastructure] repositories/ + ingest/ + config/
```

Modelo de dados **raw + canonical** (ADR 0004): payloads externos ficam intactos em `/openalex/...`; dados normalizados servem a UI em `/autores_flat/`, `/produtos/`, etc.

### 2.4 Estado da refatoração

| Frente | Foco | Status |
|--------|------|--------|
| **1** | Segurança, CORS, limpeza git | Parcial |
| **2** | Renomeações, centralização dbref, bug ORCID | Concluída |
| **3** | Pydantic, lru_cache, response_model | Parcial (docentes/discentes/projetos ✅; demais ❌) |
| **4** | Analytics em services/ + testes | Concluída |

### 2.5 Dívidas técnicas e migrações pendentes

**Backend**

- Endpoints proxy em `main.py` acessam RTDB diretamente (violam camada de repositório).
- `services/pesquisa.py` usa Firebase Admin SDK fora de `repositories/`.
- Rotas com `body: dict` sem Pydantic: veículos, linhas, pesquisas, autores, produtos.
- Handlers síncronos (`def`) — dívida consciente (ADR 0005), a corrigir com Firestore.
- Validators Pydantic v1 (`@validator`) em `domain/schemas.py`.
- Ingest como rotas HTTP, não como Cloud Run Jobs.

**Frontend**

- Auth stubbed (`AuthProvider`, `firebaseClient.js`).
- Leitura direta do RTDB em Home, Qualis, RelatorioProducao (bypass da API).
- Páginas duplicadas (`Home.jsx` vs `Home/Home.jsx`).
- Stubs Python legados em `apresentacao/components/`, `pages/`, `services/`.
- Branding inconsistente (Poshboard / 4GTAG / poshbard).

**Infraestrutura**

- Sem `Dockerfile` (referenciado no README).
- `firebase.json` aponta para `public/`, não `apresentacao/dist`.
- CI GitHub Actions com project ID divergente do `.firebaserc`.
- Migração RTDB → Firestore sem script de dados.

**Futuro documentado**

- Adapter Lattes + agentes agno (`functions/ingest/lattes/`).
- JWT auth no backend.
- Cloud Scheduler + Cloud Run Jobs para coleta periódica.

---

## 3. O que é "transpilação" neste contexto

**Transpilação** (source-to-source translation) converte código de uma sintaxe, API ou plataforma para outra **sem mudar a linguagem de programação**, ou traduz entre linguagens mantendo a semântica. No Poshboard, os cenários relevantes são:

| Cenário | Tipo | Exemplo no projeto |
|---------|------|-------------------|
| RTDB → Firestore | Mudança de API/SDK | `db.reference()` → `collection().document()` |
| Pydantic v1 → v2 | Modernização de sintaxe | `@validator` → `@field_validator` |
| sync → async FastAPI | Refatoração estrutural | `def get_docente` → `async def get_docente` |
| React legado → padrão atual | Consolidação de componentes | Duplicatas de páginas |
| Python stubs → React | Conversão de linguagem | Stubs em `apresentacao/pages/*.py` |

Ferramentas puramente determinísticas funcionam bem quando existe **receita formal** (regras fixas). Ferramentas com IA funcionam melhor quando a transformação exige **contexto de domínio** (regras de negócio bibliométricas, modelo raw/canonical, enums `TipoDocente`).

---

## 4. Panorama de ferramentas

### 4.1 Categorias

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODERNIZAÇÃO DE CÓDIGO                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Determinística  │ Híbrida (IA +   │ Agentes enterprise          │
│ (receitas/LST)  │  receitas)      │ (multi-repo, legado)        │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ OpenRewrite     │ Moderne/Moddy   │ AWS Transform               │
│ bump-pydantic   │ GitHub Copilot  │ IBM watsonx Code Assistant  │
│ ESLint codemods │ Cursor          │ EltegraAI                   │
│ ruff --fix      │ Claude Code     │ AAMF                        │
│ CodePorting.ai  │ Refact.ai       │ TSRI JANUS Studio           │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 4.2 Matriz comparativa (ferramentas com IA)

| Ferramenta | Tipo | Linguagens principais | Uso de IA | Custo típico | Adequação ao Poshboard |
|------------|------|----------------------|-----------|--------------|------------------------|
| **OpenRewrite + Moderne** | Receitas determinísticas + agente Moddy | Java, JS/TS, YAML; Python via Moderne CLI | Moddy seleciona receitas via NL | OSS + enterprise | Média — útil para JS/TS no frontend |
| **bump-pydantic** | CLI determinística | Python | Não | Gratuito | **Alta** — `@validator` restantes |
| **AWS Transform** | Agente cloud | Java, Python, Node, mainframe | Sim (agentic) | AWS pay-per-use | Baixa agora — overkill para monorepo pequeno |
| **GitHub Copilot / Workspace** | Assistente IDE | Multi-linguagem | Sim | ~$19/mês | **Alta** — padrões do repo |
| **Cursor** | IDE com agente | Multi-linguagem | Sim | ~$20/mês | **Alta** — refatoração multi-arquivo |
| **Claude Code** | CLI agente | Multi-linguagem | Sim | Pay-per-token | **Alta** — tarefas complexas (Firestore) |
| **Refact.ai** | Agente OSS/IDE | Python, JS, etc. | Sim | OSS + cloud | Média — refatoração autônoma |
| **AAMF** | Framework agentes | Qualquer → qualquer | Sim (fleet) | OSS | Baixa — projetado para codebases enormes |
| **EltegraAI** | Plataforma enterprise | COBOL, PowerBuilder, .NET | Sim (knowledge graph) | Enterprise | Baixa — legado corporativo |
| **CodePorting.ai** | Transpilador web | Apex, 4D, Lisp | Sim | SaaS | Baixa — linguagens não usadas |
| **IBM watsonx Code Assistant for Z** | COBOL → Java | COBOL, Java | Sim (Granite LLM) | IBM Cloud | Nenhuma |
| **fscopy** | CLI Firestore | Firestore | Não | Gratuito | Média — pós-migração entre projetos GCP |

---

## 5. Ferramentas detalhadas

### 5.1 Ferramentas determinísticas (base da modernização)

#### bump-pydantic (Pydantic team)

Ferramenta oficial para migrar código Pydantic v1 → v2. Aplica regras nomeadas (BP001–BP010): substitui `@validator` por `@field_validator`, `Config` por `model_config`, imports obsoletos, etc.

```bash
pip install bump-pydantic
bump-pydantic --diff functions/domain/
bump-pydantic functions/domain/
```

**Aplicação no Poshboard:** Frente 3 — corrigir validators restantes em `domain/schemas.py` antes de expandir schemas para veículos, linhas e pesquisas.

#### OpenRewrite (Moderne)

Motor open-source baseado em **Lossless Semantic Tree (LST)** — representação do código com precisão de compilador. Receitas são programas determinísticos: buscam padrões no LST e aplicam transformações composáveis e testáveis.

- Suporte nativo: Java, Kotlin, Groovy, JavaScript, TypeScript, YAML, JSON, etc.
- Python: receitas limitadas no OSS; Moderne CLI oferece suporte adicional para projetos open-source.
- **Moddy**: agente que recebe linguagem natural ("upgrade Spring Boot 3.5"), seleciona receitas OpenRewrite e executa em múltiplos repositórios.

**Aplicação no Poshboard:** Renomeações em massa no frontend (consolidar imports duplicados), atualizações de dependências React/Vite, migração de padrões ESLint. Menos útil para a camada Python/Firebase.

#### ruff (Python)

Linter/formatter com `--fix` para correções automáticas. Não é transpilador, mas acelera padronização antes de migrações maiores.

**Aplicação:** Unificar imports, remover código morto, aplicar regras de estilo antes da Frente 3.

---

### 5.2 Assistentes de código com IA (transpilação assistida)

Estes não garantem determinismo, mas **aprendem padrões do repositório** — crítico para um projeto com ADRs e convenções próprias.

#### Cursor

IDE fork do VS Code com indexação do repositório, edição multi-arquivo (Composer/Agent) e contexto amplo (~200K tokens). Ideal para:

- Reescrever `repositories/` para Firestore mantendo interfaces CRUD.
- Consolidar páginas React duplicadas seguindo providers existentes.
- Gerar testes espelhando `tests/test_docentes.py` para novas rotas.

**Vantagem:** O projeto já documenta frentes e ADRs — esses arquivos podem ser incluídos no contexto do agente.

#### GitHub Copilot / Copilot Workspace

Copilot Chat para refatorações pontuais; **Copilot Workspace** para tarefas de 3–5 arquivos com plano + PR draft. Estudos indicam que Workspace aprende padrões locais (ex.: decorator `handle_errors`) melhor que prompts genéricos.

**Aplicação:** Implementar endpoints Pydantic nas rotas restantes (Frente 3.2–3.4) espelhando `docentes.py`.

#### Claude Code

Agente terminal-first, forte em raciocínio multi-etapa. Adequado para:

- Script de migração RTDB → Firestore com mapeamento raw/canonical.
- Converter handlers sync → async após repositórios Firestore.
- Gerar `Dockerfile` + ajustar CI conforme ADR 0003.

#### Refact.ai

Agente open-source (IDE plugin ou self-hosted) com planejamento autônomo de tarefas, refatoração e geração de testes. Alternativa a Copilot/Cursor para equipes que precisam de deploy on-premise.

---

### 5.3 Plataformas enterprise com IA agêntica

#### AWS Transform

Serviço AWS com IA agêntica para modernização em escala: análise de dependências, planos de migração, conversão de linguagens (ex.: mainframe COBOL → Java), testes automatizados. Oferece também **transformações customizadas** via chat — o agente aprende com documentação e exemplos de código da organização.

**Relevância:** Baixa para o porte atual do Poshboard, mas útil se o deploy consolidar no GCP/AWS com pipelines de modernização contínua (atualizações de SDK Firebase, Python runtime).

#### AAMF (Autonomous Agent Migration Framework)

Framework OSS que decompõe codebases em um DAG de tarefas, executa agentes em fases (indexação → migração → verificação de paridade → commit), com checkpointing. Projetado para traduzir codebases inteiros entre linguagens.

**Relevância:** Experimental/overkill para ~15K LOC; interessante como referência arquitetural para a futura migração RTDB → Firestore em fases.

#### EltegraAI

Plataforma enterprise que constrói um **knowledge graph** do sistema legado (regras de negócio, dependências) antes de gerar código moderno — abordagem "determinística primeiro, LLM depois" para reduzir alucinações.

**Relevância:** Baixa (COBOL, PowerBuilder, SAP); o conceito de knowledge graph é analogamente útil: mapear o modelo raw/canonical antes de automatizar a migração Firestore.

#### IBM watsonx Code Assistant for Z

COBOL → Java via VS Code + LLM Granite. Não aplicável ao stack Python/React.

#### CodePorting.ai Modernizer

Transpilador web com IA para sintaxes específicas (Apex, 4D, Lisp). Modelo "cole o código, receba código modernizado". Não cobre FastAPI/Firebase.

---

### 5.4 Ferramentas específicas para Firebase/GCP

#### Migração RTDB → Firestore

A documentação oficial do Firebase **não oferece migração automatizada** — os modelos de dados são fundamentalmente diferentes (JSON tree vs collections/documents). O fluxo recomendado:

1. Mapear estrutura RTDB → schema Firestore (collections, subcollections, índices).
2. Exportar JSON do RTDB.
3. Script customizado com Firebase Admin SDK (batch writes, 500 ops/request).
4. Período de dual-write via Cloud Functions.
5. Reescrever `repositories/` para `google.cloud.firestore`.

**Onde a IA ajuda:** Gerar o script de transformação e reescrever repositórios — tarefa ideal para Cursor/Claude Code com ADR 0001 e `ARCHITECTURE.md` no contexto. Ferramentas determinísticas não resolvem o mapeamento semântico sozinhas.

#### fscopy

CLI para copiar collections Firestore entre projetos Firebase, com transforms JS/TS, filtros, resume e dry-run. Útil **após** a migração inicial, para sincronizar ambientes (dev → staging → prod).

---

## 6. Mapeamento: ferramentas → frentes do Poshboard

| Necessidade | Frente/ADR | Ferramenta recomendada | Tipo |
|-------------|-----------|------------------------|------|
| Corrigir `@validator` Pydantic v1 | Frente 3 | **bump-pydantic** | Determinística |
| Adicionar schemas Pydantic nas rotas restantes | Frente 3 | **Cursor / Copilot Workspace** | IA assistida |
| Substituir `body: dict` por modelos tipados | Frente 3 | **Cursor / Copilot** | IA assistida |
| Reescrever `repositories/` para Firestore | ADR 0001 | **Claude Code / Cursor** | IA assistida |
| Script migração dados RTDB → Firestore | ADR 0001 | **Claude Code** + Admin SDK | IA + script manual |
| Handlers sync → async | ADR 0005 | **Cursor** (após Firestore) | IA assistida |
| Consolidar páginas React duplicadas | Frontend | **OpenRewrite** (TS) ou **Cursor** | Misto |
| Remover stubs Python legados | Frontend | **Cursor Agent** | IA assistida |
| Centralizar fetch (remover RTDB direto no frontend) | Frontend | **Copilot Workspace** | IA assistida |
| Gerar testes para novas rotas | Frente 4 | **Copilot / Cursor** | IA assistida |
| Dockerfile + Cloud Run | ADR 0003 | **Claude Code** | IA assistida |
| Corrigir CI/CD (firebase.json, project ID) | Frente 1 | Manual ou **Cursor** | Misto |
| Adapter Lattes + agentes agno | Futuro | **agno** (já planejado) + **Cursor** | IA nativa |
| Atualizar dependências React/Vite | Infra | **npm-check-updates** + **OpenRewrite** | Determinística |

---

## 7. Estratégia recomendada para o Poshboard

### 7.1 Princípio 95/5

Seguindo a prática consolidada na comunidade (OpenRewrite vs Copilot):

- **95% do "trabalho mecânico"** → ferramentas determinísticas (`bump-pydantic`, ruff, receitas OpenRewrite, scripts Firebase Admin SDK).
- **5% da lógica contextual** → IA (Cursor, Copilot, Claude Code) com ADRs e frentes no prompt.

Isso reduz alucinações, custo de tokens e tempo de revisão.

### 7.2 Ordem de execução sugerida

```
Fase A — Determinística (1–2 dias)
├── bump-pydantic em functions/domain/
├── ruff check --fix functions/
└── Remover stubs/arquivos legados identificados

Fase B — IA assistida, escopo fechado (1–2 semanas)
├── Frente 3: schemas + response_model nas rotas restantes
├── Consolidar frontend (páginas duplicadas, env vars)
└── Testes espelhando padrão existente (54+ tests)

Fase C — Migração Firestore (2–4 semanas)
├── Mapeamento RTDB → Firestore (documento de schema)
├── Reescrita repositories/ (IA + revisão humana)
├── Script de migração de dados (Admin SDK)
├── Dual-write period
└── ADR 0005: async handlers

Fase D — Infra (paralelo)
├── Dockerfile + Cloud Run
├── Corrigir firebase.json e CI
└── Cloud Run Jobs para ingest
```

### 7.3 Guardrails ao usar IA para transpilação

1. **Sempre incluir contexto:** ADRs, `ARCHITECTURE.md`, frente correspondente.
2. **Diff pequeno, PR revisável:** Uma entidade por PR (ex.: só `veiculos.py`).
3. **Testes antes e depois:** Rodar `pytest` após cada transformação; meta: manter 54+ passed.
4. **Não confiar em equivalência funcional sem teste:** Especialmente na migração Firestore (queries compostas vs full scan).
5. **Preferir refatoração a reescrita:** Alinhado ao ADR 0002 — mover código, não reinventar arquitetura.

### 7.4 O que evitar

| Abordagem | Por quê |
|-----------|---------|
| AWS Transform / EltegraAI / AAMF para todo o repo | Custo e complexidade desproporcionais |
| Transpilação automática RTDB → Firestore "one-click" | Não existe; modelos incompatíveis |
| Reengenharia total guiada por IA | Viola ADR 0002; alto risco de regressão |
| IA sem ADRs no contexto | Gera código que ignora raw/canonical e camadas |

---

## 8. Casos de uso concretos

### 8.1 Frente 3 — Expandir Pydantic para `veiculos.py`

**Prompt sugerido (Cursor/Copilot):**

> Com base em `api_routes/docentes.py` e `domain/schemas.py`, adicione modelos `VeiculoCreate`/`VeiculoOut` usando enums de `domain/types.py`. Substitua `body: dict` por modelos Pydantic, adicione `response_model`, use `@lru_cache` para o CRUD. Não altere a lógica de negócio. Siga ADR 0002.

**Ferramenta:** Copilot Workspace (3–5 arquivos) ou Cursor Composer.

### 8.2 ADR 0001 — Protótipo de repositório Firestore

**Prompt sugerido (Claude Code):**

> Reescreva `repositories/docente_crud.py` para usar `google.cloud.firestore` mantendo a mesma interface pública de `BaseCRUD`. Preserve suporte a `find_by_orcid` com query indexada. Consulte ADR 0001 e `common/dbref.py`.

**Ferramenta:** Claude Code ou Cursor Agent (multi-arquivo + testes).

### 8.3 Frontend — Eliminar leitura direta do RTDB

**Prompt sugerido:**

> Em `pages/Home.jsx` e `pages/Qualis.jsx`, substitua fetch direto ao RTDB por chamadas à API FastAPI usando `VITE_API_URL`, seguindo o padrão de `TeacherProvider.jsx`.

**Ferramenta:** Cursor; validar com build Vite.

---

## 9. Ferramentas complementares (não-IA, mas essenciais)

| Ferramenta | Função |
|------------|--------|
| **pytest + httpx** | Validação pós-migração (já em uso) |
| **Firebase Emulator Suite** | Testes de integração RTDB/Firestore |
| **PlantUML (`uml_packages.py`)** | Visualizar impacto de mudanças arquiteturais |
| **git filter-repo / BFG** | Limpeza de credenciais (Frente 1.1) |
| **Firebase CLI** | Export RTDB, deploy Hosting |
| **agno** (planejado) | Agentes IA para scraping Lattes — caso de uso nativo de IA no domínio |

---

## 10. Conclusão

O Poshboard **não precisa** de plataformas enterprise de transpilação (AWS Transform, EltegraAI, AAMF) — o codebase é pequeno, o stack já é moderno (Python 3.11+, React 19, FastAPI), e a estratégia arquitetural está definida nos ADRs.

O ganho real vem de combinar:

1. **Ferramentas determinísticas** onde existem receitas (`bump-pydantic`, OpenRewrite para TS, ruff).
2. **Assistentes de IA no IDE** (Cursor, Copilot, Claude Code) para refatorações contextuais alinhadas às quatro frentes.
3. **Scripts customizados** para a migração RTDB → Firestore (única migração sem ferramenta pronta).
4. **agno** no futuro para o pipeline Lattes — IA aplicada ao domínio, não à infraestrutura.

A documentação existente (`frentes-refatoracao.md`, ADRs, PRD) é um **ativo estratégico**: funciona como "knowledge graph" leve que orienta tanto desenvolvedores quanto agentes de IA, reduzindo o risco de modernização descoordenada.

---

## 11. Referências

### Documentação interna
- `docs/ARCHITECTURE.md`
- `docs/adr/0001-firestore-em-vez-de-rtdb.md` — migração de banco
- `docs/adr/0002-manutencao-sem-reengenharia.md` — escopo de mudanças
- `docs/adr/0005-handlers-sincronos-divida-tecnica.md` — sync → async
- `docs/frentes-refatoracao.md` — programa de refatoração
- `docs/prd-refatoracao.md` — requisitos de qualidade

### Ferramentas e plataformas
- [OpenRewrite](https://docs.openrewrite.org/) — receitas determinísticas, LST
- [Moderne / Moddy](https://www.moderne.ai/) — modernização em escala com agente IA
- [bump-pydantic](https://github.com/pydantic/bump-pydantic) — migração Pydantic v1 → v2
- [AWS Transform](https://aws.amazon.com/transform/) — modernização agêntica (custom + mainframe)
- [AAMF](https://github.com/jafreck/AAMF) — framework de migração autônoma
- [EltegraAI](https://intellyx.com/2026/05/25/eltegraai-rethinking-legacy-modernization-with-knowledge-graphs-and-reverse-engineering/) — knowledge graph + agentes
- [Firebase: RTDB → Firestore](https://firebase.google.com/docs/firestore/firestore-for-rtdb) — guia oficial de migração
- [fscopy](https://github.com/FaZeTitans/fscopy) — CLI cópia Firestore entre projetos
- [CodePorting.ai Modernizer](https://products.codeporting.ai/pt/modernizer/apex) — transpilação sintática com IA
- [IBM watsonx Code Assistant for Z](https://www.ibm.com/br-pt/think/architectures/patterns/genai-code-generation-z) — COBOL → Java
- [Refact.ai](https://refact.ai/) — agente de código open-source

### Artigos e comparativos
- OpenRewrite vs Copilot para migrações — determinismo vs probabilidade em framework upgrades
- GitHub Copilot Workspace — aprendizado de padrões locais do repositório
- IN-COM Data Systems — panorama de ferramentas de modernização de legado (2025)
