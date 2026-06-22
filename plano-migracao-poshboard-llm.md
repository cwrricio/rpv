# Plano de Migração e Experimento com LLMs — Poshboard

**Projeto:** Poshboard (RPV)
**Base:** Relatório Final SSQM (2026-06-08)
**Mudança-alvo:** LONG-01 — *Operar versão sem Firebase em ambiente próprio ou híbrido*
**Natureza:** plano de migração para arquitetura nova **+** desenho experimental para medir eficiência e eficácia de LLMs no processo de migração
**Janela:** 2 semanas (Semana 1 = preparação e baseline; Semana 2 = execução assistida por LLM e coleta de métricas)

---

## 0. Premissas de escopo (confirmar / ajustar)

Para não travar o plano, foram fixadas duas decisões. Se alguma divergir da sua intenção, é só apontar.

1. **Alvo "próprio" primeiro, "híbrido" documentado.** O alvo de referência é *self-hosted* com Docker Compose (PostgreSQL + Redis + app + proxy reverso) num VPS/servidor próprio. O caminho **híbrido** é descrito como variação (imagem em registry neutro + deploy em Cloud Run/PostgreSQL gerenciado), de modo que nenhuma dependência fique presa a Firebase/Google.
2. **Comparação experimental.** O experimento compara a execução **assistida por LLM** contra a **estimativa humana de horas do próprio relatório** (baseline de esforço) e, opcionalmente, entre **≥ 2 modelos/ferramentas** de LLM. O critério de qualidade usa os mesmos índices SSQM já calculados, medindo o *delta* antes/depois.

---

## 1. Por que esta mudança é o melhor caso de teste

O relatório mostra que o lock-in do Poshboard **não está na linguagem nem nos frameworks** (FastAPI, React, libs OSS são portáveis), e sim na **concentração de dados, credenciais e operação em Firebase**. Sair do Firebase exige tocar simultaneamente em: persistência (RTDB→PostgreSQL), padrão de acesso (SDK espalhado → portas/adaptadores), frontend (fallback direto → só API), identidade (Google ADC → segredos próprios) e deploy (Firebase Hosting → containers). É uma transformação **ampla, mensurável e com baseline numérico pronto** (SSQMScore, IDAN, IDC, IP, CLSn) — condições ideais para avaliar o quanto uma LLM consegue executar de migração real, e com que qualidade.

---

## 2. Arquitetura AS-IS (resumo do relatório)

```text
Frontend React/Vite ──(REST)──> Backend FastAPI ──> Firebase Admin SDK ──> Firebase RTDB
        └────────────(fallback direto *.firebaseio.com/*.json)───────────────┘
Backend ──> APIs externas (OpenAlex / ORCID / Crossref / Semantic Scholar)
Credenciais: Google ADC / service account | Deploy: Firebase Hosting + GitHub Actions
```

> **Linha de partida real (importante para as métricas).** O relatório descreve o estado AS-IS *original*. Porém a branch `SSQM` já executou a **Parte 1 / roadmap de curto prazo** (ver `docs/SSQM-IMPLEMENTACAO.md`): portas/adaptadores (`StoragePort` + `FirebaseRTDBAdapter`), frontend **só-API** (0 `firebaseio.com`/`VITE_RTDB_URL` em `apresentacao/src`), export versionado, `PostgresAdapter` inicial (`kv_store`) e Docker Compose (Postgres+API+frontend), com `65 passed, 1 skipped`. O experimento **não parte do zero**: o repositório congelado da Semana 1 deve ser este estado pós-Parte-1, e os baselines de esforço/acoplamento abaixo precisam ser lidos como **esforço restante**, não esforço total do relatório. Ver §4.1.

Acoplamentos críticos a eliminar (mapeados aos smells do relatório):

| Smell | Evidência | Meta pós-migração |
|---|---|---|
| CLS-01 RTDB como persistência | `config/firebase_admin_init.py`, `repositories/base.py`, `main.py` | PostgreSQL canônico |
| CLS-02 SDK Firebase vazando | `firebase_admin.db` em services/scripts/repos | 0 chamadas fora do adaptador legado |
| CLS-03 Frontend → RTDB direto | `VITE_RTDB_URL`, `*.firebaseio.com/*.json` | 0 chamadas; só API |
| CLS-04 Credenciais Google ADC | `GOOGLE_APPLICATION_CREDENTIALS`/ADC | Segredos próprios (env/Vault) |
| CLS-05 Hosting/deploy Firebase | `firebase.json`, `action-hosting-deploy` | Container + proxy próprio |
| CLS-06 Ingestão sem cache | módulos `functions/ingest/` | Cache/snapshot + retries |

---

## 3. Arquitetura TO-BE (alvo: sem Firebase, próprio/híbrido)

Arquitetura **hexagonal (portas e adaptadores)**: domínio e regras de negócio isolados da infraestrutura, com adaptadores plugáveis.

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

### Stack alvo

| Camada | AS-IS | TO-BE | Componente |
|---|---|---|---|
| Persistência | Firebase RTDB | PostgreSQL canônico | `postgres:16` + SQLAlchemy + migrations (Alembic) |
| Acesso a dados | SDK em várias camadas | Portas + adaptadores | `RepositoryPort` ↔ `PostgresAdapter` / `FirebaseAdapter` (legado) |
| Frontend | API + fallback RTDB | Só API | Remover `firebase` do `package.json` e `VITE_RTDB_URL` |
| Ingestão | Chamadas diretas | Worker + fila + cache | Redis + RQ/Celery, timeouts, retries, snapshot |
| Identidade/segredos | Google ADC | Segredos próprios | `.env`/Vault; Keycloak opcional p/ login real |
| Deploy | Firebase Hosting | Containers próprios/híbrido | Docker Compose (próprio) ou imagem→Cloud Run (híbrido) |
| Proxy/entrega | Firebase Hosting | Reverse proxy | Caddy ou Nginx |
| CI/CD | GitHub Actions Firebase | Pipeline portável | build→test→imagem→deploy (GitHub/GitLab/Jenkins) |
| Observabilidade | Não evidenciada | Própria | logs estruturados, `/health`, métricas Prometheus, backup testado |

### Padrão de migração: *Strangler + Parallel-run*

O adaptador Firebase **não é removido no dia 1**. Ele permanece atrás da mesma `RepositoryPort` enquanto o `PostgresAdapter` é construído, permitindo **leitura/escrita dupla** e **comparação automática de fidelidade** entre RTDB e PostgreSQL. Só depois de validar paridade o Firebase é desativado. Isso torna a migração auditável e dá um instrumento de medição de eficácia (diff RTDB×PG) gratuito.

---

## 4. Decomposição em Work Packages (WP)

Cada WP é uma unidade de trabalho que a LLM executará na Semana 2 e cuja saída é avaliada de forma independente. O **baseline (h)** vem das estimativas do próprio relatório e serve de referência de esforço humano.

| WP | Objetivo | Entrada | Tarefa da LLM | Critério de aceite | Baseline relatório |
|---|---|---|---|---|---|
| WP-1 | Mapa de nós RTDB → modelo canônico | export JSON do RTDB | Inferir schema relacional (tabelas, FKs, índices) e documentá-lo | Schema cobre 100% dos nós; revisão humana aprova | 16–32 h (MED curto prazo) |
| WP-2 | Portas de repositório + adaptador PostgreSQL | código atual `repositories/` | Definir interfaces e implementar adaptador SQLAlchemy + Alembic | App sobe contra PG; CRUD passa nos testes | 120–220 h (médio prazo) |
| WP-3 | Script ETL RTDB→PostgreSQL c/ validação e rollback | export RTDB + schema WP-1 | Gerar extrator/transformador/carga + verificação de paridade + rollback | Paridade de linhas e campos ≥ meta; rollback funciona | 80–160 h (médio prazo) |
| WP-4 | Centralizar acesso Firebase em adaptador único | `firebase_admin.db` espalhado | Refatorar services/scripts p/ usar a porta; encapsular SDK | 0 `firebase_admin.db` fora do adaptador legado | 40–80 h (curto prazo) |
| WP-5 | Desacoplar frontend do RTDB | telas React c/ `*.firebaseio.com` | Substituir chamadas diretas por chamadas à API; remover SDK | 0 `firebaseio.com`/`VITE_RTDB_URL`; UI funcional | 24–40 h + 8–16 h |
| WP-6 | Identidade/segredos sem Google ADC | `firebase_admin_init.py`, README | Migrar para segredos próprios; documentar | App autentica sem ADC; sem credencial Google em runtime | 40–120 h (opcional Keycloak) |
| WP-7 | Containerização própria/híbrida | app backend+frontend | Dockerfiles + `docker-compose` (PG+Redis+app+proxy); variação híbrida | `compose up` saudável; health check verde | 40–80 h |
| WP-8 | Ingestão resiliente (cache/fila/retries) | `functions/ingest/` | Cliente unificado c/ timeout/retry/cache + worker | Ingestão tolera falha de API externa; snapshot grava | 80–160 h + 32–64 h |
| WP-9 | CI/CD portável + observabilidade + backup | workflows atuais | Pipeline build→test→imagem→deploy; logs/métricas/backup testado | Pipeline roda fora do Firebase; restore testado | 24–48 h + 80–160 h |
| WP-10 | Desligar Firebase e re-scorar SSQM | sistema migrado | Remover adaptador legado; reaplicar checklist SSQM | 0 dependência Firebase em runtime; novo SSQMScore | 160–320 h (LONG-01) |

> No experimento de 2 semanas o objetivo **não é concluir as 952–1.948 horas estimadas** (faixa total do relatório), e sim executar o máximo de WPs com LLM e **medir** o quanto cada uma rendeu por hora real, com que qualidade e com quanta intervenção humana — extrapolando o ganho frente ao baseline.

### 4.1. Estado atual por WP — esforço já realizado × restante

A **Parte 1** (commit atual da branch `SSQM`) já entregou trabalho que sobrepõe vários WPs. Para que o *fator de aceleração* não seja inflado contabilizando trabalho pré-existente como mérito da LLM, cada WP carrega abaixo seu estado de partida. O **baseline efetivo** do experimento é o esforço **restante**, não o do relatório.

| WP | Estado na branch `SSQM` | Evidência | Baseline efetivo (restante) |
|---|---|---|---|
| WP-1 | **Parcial** — mapa de coleções e dívidas em `DATA_MODEL.md`; falta schema relacional normalizado (FKs/índices) | `docs/DATA_MODEL.md` | baixo (formalizar schema) |
| WP-2 | **Parcial** — `StoragePort` + `PostgresAdapter` com `kv_store` genérico; falta modelo canônico em tabelas/Alembic | `functions/adapters/postgres_adapter.py` | médio-alto (modelo + migrations) |
| WP-3 | **Não iniciado** — export existe (`export_rtdb.py`), mas ETL→PG com paridade/rollback não | `scripts/export_rtdb.py` | cheio (80–160 h) |
| WP-4 | **Quase pronto** — `firebase_admin.db` removido de services/main; resta dívida em `find_by_orcid`/`PesquisaService.listar` via escape hatch | `SSQM-IMPLEMENTACAO.md` | baixo (fechar dívida) |
| WP-5 | **Concluído** — frontend só-API, `firebase` fora do `package.json`, `grep`=0 | `SSQM-IMPLEMENTACAO.md` | ~0 (só validar/regressão) |
| WP-6 | **Não iniciado** — segredos próprios/identidade ainda em ADC | — | cheio (40–120 h) |
| WP-7 | **Parcial** — Dockerfiles + `docker-compose` (PG+API+frontend) prontos; falta proxy reverso, health/observabilidade e variação híbrida | `docker-compose.yml` | médio (proxy + híbrido) |
| WP-8 | **Não iniciado** — ingestão intocada por requisito explícito | `functions/ingest/*` | cheio (80–160 + 32–64 h) |
| WP-9 | **Não iniciado** — CI/CD ainda Firebase; sem observabilidade/backup testado | — | cheio (24–48 + 80–160 h) |
| WP-10 | **Não iniciado** — adaptador legado ainda presente; SSQM não re-scorado | — | cheio (160–320 h) |

> **Consequência metodológica:** WP-5 e WP-4 servem melhor como **casos de validação/regressão** (a LLM mantém o ganho já existente?) do que como casos de geração. Os casos de geração de maior valor experimental — onde o teto de autonomia da LLM é realmente testado — são **WP-2 (modelo canônico), WP-3 (ETL+paridade), WP-8 (ingestão resiliente) e WP-10 (desligar Firebase + re-score)**.

---

## 5. Plano experimental — avaliando eficiência e eficácia das LLMs

### 5.1 Desenho do experimento

- **Unidade experimental:** o WP (work package). Cada WP é uma "tarefa de migração" pontuável.
- **Condições comparadas (escolher conforme recurso disponível):**
  - **C0 — Baseline humano:** estimativa de horas do relatório (referência, não re-executada).
  - **C1 — LLM-assistida (humano no loop):** desenvolvedor + LLM, o cenário realista.
  - **C2 — LLM-autônoma (agente):** LLM executa o WP com mínima supervisão (mede teto de autonomia).
  - **C3 — Modelo B:** repetir C1/C2 com outra LLM/ferramenta para comparação entre modelos.
- **Controles de validade:** repositório **congelado** (commit/tag fixo — **o estado pós-Parte-1 da branch `SSQM`**, não o AS-IS original do relatório; ver §4.1) e **export RTDB fixo** antes da Semana 2; mesmo enunciado de WP para todas as condições; suíte de testes "golden" e rubrica SSQM definidas **antes** de qualquer execução (evita ajuste pós-hoc). Registrar no congelamento o **acoplamento de partida** (`grep` já = 0 no frontend; dívida residual em `find_by_orcid`/`PesquisaService.listar`) para que a métrica meça só o que a LLM remove.
- **Replicação:** rodar cada WP em condição agentica ≥ 2 vezes para estimar variância/reprodutibilidade.

### 5.2 Framework de métricas

**A. Eficácia (a saída funciona e tem qualidade)**

| Métrica | Definição | Instrumento | Meta |
|---|---|---|---|
| Taxa de testes verdes | % da suíte golden que passa na saída da LLM | `pytest` | ≥ 95% |
| Fidelidade de dados | paridade de linhas + diff campo a campo RTDB×PG | script de validação WP-3 | ≥ 99,9% linhas; 0 divergência crítica |
| Redução de acoplamento | nº de `firebase_admin.db` + `firebaseio.com` + `VITE_RTDB_URL` restantes | `grep -rn` | 0 (fora do adaptador legado) |
| Conformidade arquitetural | domínio não importa infraestrutura (direção de dependência) | lint de dependência + rubrica | 0 violações |
| Build & deploy | imagem builda e `compose up` fica saudável | CI + health check | sucesso booleano |
| Segurança/regressão | sem segredo em código, sem nova vulnerabilidade | scanner (ex.: `gitleaks`, `pip-audit`) | 0 achados altos |
| Completude vs. aceite | % dos critérios de aceite do WP atendidos **sem** correção humana | checklist do WP | medida-chave de eficácia |

**B. Eficiência (custo, esforço e velocidade)**

| Métrica | Definição | Instrumento | Como interpretar |
|---|---|---|---|
| Tempo real por WP | wall-clock do início ao aceite | timestamps | comparar ao baseline (h) do relatório |
| Fator de aceleração | baseline_h ÷ tempo_real_h | cálculo | > 1 = ganho sobre estimativa humana |
| Custo de tokens / API | tokens e custo monetário por WP | logs da ferramenta | custo por WP entregue |
| Iterações até verde | nº de rodadas de prompt até passar no aceite | contagem manual | menos = mais eficiente |
| Taxa de intervenção humana | linhas editadas pelo humano ÷ linhas finais (autoria via `git`) | `git blame`/diff | quanto a LLM realmente entregou |
| Taxa de retrabalho | nº de saídas descartadas/regeradas | log | instabilidade do processo |

**C. Processo e confiabilidade**

| Métrica | Definição | Instrumento |
|---|---|---|
| Alucinações | nº de APIs/arquivos/imports inexistentes inventados | revisão |
| Aderência à instrução | % de requisitos do WP de fato endereçados | checklist |
| Reprodutibilidade | variância de resultado entre execuções repetidas | comparação C2/C3 |
| Nível de autonomia | escala 0–4 (ver Anexo C) | classificação por WP |

### 5.3 Métrica-âncora: *delta* nos índices SSQM (antes × depois)

O resultado mais forte do estudo é mostrar a migração **movendo os números do próprio relatório**. Baseline já calculado:

| Índice | Baseline (relatório) | Direção desejada | Alvo pós-migração (referência) |
|---|---:|---|---:|
| SSQMScore | 0,43 (43,3%) | ↑ | ≥ 0,70 |
| IDAN | 0,55 | ↓ | ≤ 0,30 |
| IDC (dependência crítica) | 0,53 | ↓ | ≤ 0,30 |
| IP (portabilidade) | 0,58 | ↑ | ≥ 0,80 |
| CLSn (smells normalizados) | 0,66 | ↓ | ≤ 0,20 |

Baseline completo das 9 dimensões (checklist do relatório, escala `0–2` por item, total `/90`):

| Dimensão | Baseline | Alvo da migração | Onde o WP atua |
|---|---:|---|---|
| ST — Soberania Tecnológica | 3/10 | ↑ (PostgreSQL/stack aberto) | WP-2, WP-7 |
| SO — Soberania Operacional | 1/10 | ↑↑ (contingência, health, proxy próprio) | WP-7, WP-9 |
| SD — Soberania de Dados | 2/10 | ↑↑ (PG canônico, export, backup testado) | WP-2, WP-3, WP-9 |
| SA — Soberania Arquitetural | 4/10 | ↑ (portas/adaptadores, 0 SDK vazado) | WP-2, WP-4 |
| SI — Soberania de IA | 10/10 | = (sem IA em produção) | — |
| SDV — Soberania de Desenvolvimento | 8/10 | ↑ (CI/CD portável) | WP-9 |
| SK — Soberania de Conhecimento | 6/10 | ↑ (docs/ADR atualizados) | todos |
| SE — Soberania de Ecossistema | 3/10 | ↑ (sair da concentração Google) | WP-6, WP-10 |
| SS — Soberania Estratégica | 2/10 | ↑ (plano formal executado) | WP-10 |

> **Ressalva ao interpretar o SSQMScore:** o SI=10/10 (não há IA acoplada em produção) **infla a média** e mascara o risco real, concentrado em dados/operação/infra. Ao reportar o *delta* em WP-10, apresentar **também** o subconjunto **SO+SD+SE+SA** (as 4 dimensões que a migração efetivamente move: baseline 10/40 = 0,25) além do SSQMScore global — assim o ganho não fica diluído pelo teto artificial do SI. As dimensões que a migração deve elevar diretamente são exatamente essas quatro. A LLM reaplica o checklist em WP-10 e o *delta* é a medida de eficácia de mais alto nível — e o melhor argumento do experimento.

### 5.4 Scorecard por WP (template para preencher na Semana 2)

```text
WP-__  | Condição: C1/C2/C3  | Modelo/ferramenta: ______  | Execução nº: __
------------------------------------------------------------------------------
EFICÁCIA
  Testes verdes ............ ____%      Acoplamento restante ...... ____
  Fidelidade de dados ...... ____%      Conformidade arq. ......... ____
  Build/deploy ............. OK/Falha   Segurança ................. ____
  Critérios de aceite sem correção ..... ____ / ____
EFICIÊNCIA
  Tempo real ............... ____ h     Baseline relatório ........ ____ h
  Fator de aceleração ...... ____x      Tokens/custo .............. ____
  Iterações até verde ...... ____       Intervenção humana ........ ____%
  Retrabalho ............... ____
PROCESSO
  Alucinações .............. ____       Aderência ................. ____%
  Autonomia (0–4) .......... ____       Reprodutibilidade ......... ____
OBSERVAÇÕES QUALITATIVAS:
  __________________________________________________________________________
```

### 5.5 Instrumentação e coleta

- **Versionamento:** cada WP entregue em branch/commit próprio; autoria humano×LLM extraída via `git`.
- **Comandos de medição automatizáveis:**
  - acoplamento: `grep -rn "firebase_admin.db\|firebaseio.com\|VITE_RTDB_URL" .`
  - testes: `pytest -q --maxfail=0`
  - fidelidade: script WP-3 (contagem + diff campo a campo do export RTDB contra o PostgreSQL)
  - segurança: `gitleaks detect`, `pip-audit`, `npm audit`
  - saúde: `docker compose up` + `curl /health`
- **Planilha mestre:** uma linha por (WP × condição × execução) consolidando os scorecards para análise agregada.

### 5.6 Critérios de sucesso do estudo

1. **Eficácia agregada:** média de "testes verdes" e "critérios de aceite sem correção" por modelo.
2. **Eficiência agregada:** fator de aceleração médio vs. baseline e custo por WP.
3. **Salto de soberania:** *delta* SSQMScore/IDAN demonstrado em WP-10.
4. **Mapa de força/fraqueza:** em quais WPs a LLM brilha (refator mecânico, geração de testes, Dockerfile) e onde falha (decisões de modelagem, validação de fidelidade, segurança) — a entrega de conhecimento mais útil do experimento.

---

## 6. Cronograma de 2 semanas

**Semana 1 — Preparação e baseline (sem LLM executando migração)**

| Dia | Atividade |
|---|---|
| 1 | Congelar repositório (tag) e export do RTDB; registrar baseline SSQM do relatório |
| 2 | Escrever/curar a suíte de testes "golden" dos endpoints e fluxos críticos |
| 3 | Definir rubrica de re-score SSQM e o script de validação de fidelidade (WP-3) |
| 4 | Montar instrumentação (planilha mestre, comandos de medição, scorecards) |
| 5 | Enunciados finais e congelados de cada WP; definir condições C1/C2/C3 e modelos |

**Semana 2 — Execução assistida por LLM e coleta**

| Dia | Atividade |
|---|---|
| 6 | WP-1 e WP-2 (schema + adaptador PostgreSQL) — coletar scorecards |
| 7 | WP-3 e WP-4 (ETL/validação + centralização do SDK) |
| 8 | WP-5 e WP-7 (frontend só-API + containerização) |
| 9 | WP-6, WP-8, WP-9 (segredos + ingestão resiliente + CI/CD/observabilidade) |
| 10 | WP-10 (desligar Firebase + re-score SSQM); consolidar planilha; análise e relatório |

---

## 7. Riscos do experimento e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Dados reais sensíveis no RTDB | Privacidade | Usar export anonimizado/amostral congelado |
| LLM "passa nos testes" sem migrar de fato | Eficácia falsa | Combinar testes + métrica de acoplamento + fidelidade + revisão humana |
| Escopo grande não cabe em 2 semanas | Cobertura parcial | Medir por WP; extrapolar ganho/h em vez de exigir conclusão total |
| Variância entre execuções | Conclusão frágil | Replicar WPs agênticos ≥ 2x; reportar variância |
| Vazamento de segredos pela LLM | Segurança | Scanner obrigatório no aceite (WP-6/WP-9) |
| Otimização para a métrica | Viés | Manter rubrica congelada antes da execução; revisão cega quando possível |

---

## Anexo A — Esboço de mapeamento RTDB → PostgreSQL

| Nó RTDB (árvore JSON) | Tabela PostgreSQL | Observação |
|---|---|---|
| `/autores/{id}` | `authors(id, nome, orcid, …)` | chaves do nó viram PK; campos viram colunas |
| `/produtos/{id}` | `works(id, titulo, doi, ano, …)` | DOI único; índice por ano |
| relação autor↔produto | `author_work(author_id, work_id)` | tabela de junção (M:N) explícita |
| `/programas/{id}` | `programs(id, nome, …)` | entidade de programa de pós |
| metadados de coleta | `ingestion_runs(id, fonte, status, …)` | rastreio de OpenAlex/ORCID/Crossref/S2 |

*Regra geral:* cada nível de chave da árvore vira PK/FK; listas viram tabelas-filhas; índices nas colunas de busca (DOI, ORCID, ano). O ETL do WP-3 percorre o export, normaliza e valida paridade campo a campo.

## Anexo B — Checklist "Firebase-zero" (gate de WP-10)

- [ ] `grep` por `firebase_admin.db` → 0 fora do adaptador legado (e adaptador legado removido)
- [ ] `grep` por `firebaseio.com` / `VITE_RTDB_URL` → 0
- [ ] `firebase` removido de `apresentacao/package.json`
- [ ] nenhuma credencial Google em runtime; `GOOGLE_APPLICATION_CREDENTIALS` não usado
- [ ] deploy roda via container próprio/registry neutro, sem Firebase Hosting
- [ ] backup/restore testado em PostgreSQL
- [ ] re-score SSQM registrado (SSQMScore, IDAN, IDC, IP, CLSn)

## Anexo C — Escala de autonomia da LLM (0–4)

| Nível | Descrição |
|---|---|
| 0 | LLM apenas sugere; humano escreve todo o código |
| 1 | LLM gera trechos; humano integra e corrige bastante |
| 2 | LLM gera o WP; humano corrige pontualmente até o aceite |
| 3 | LLM gera o WP e passa no aceite com revisão mínima |
| 4 | LLM executa o WP de ponta a ponta (incl. testes verdes) sem correção |
