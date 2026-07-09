# Relatorio Final SSQM - Poshboard

**Projeto:** Poshboard (RPV)  
**Data da avaliacao:** 2026-06-08  
**Modelo utilizado:** Software Sovereignty Quality Model (SSQM)  
**Documentos-base:** checklist SSQM, prompts de Cloud Lock-in Smells e template de avaliacao de soberania de software em `docs/`.

## 1. Visao Arquitetural Atual - AS-IS

O Poshboard e um sistema de gestao academica para programas de pos-graduacao. A arquitetura atual combina um backend Python/FastAPI, um frontend React/Vite e persistencia principal em Firebase Realtime Database (RTDB).

```text
Usuario
  |
  v
Frontend React/Vite - apresentacao/
  |                 \
  |                  \ fallback direto via REST
  v                   v
Backend FastAPI       Firebase RTDB
functions/main.py       ^
  |                     |
  v                     |
Rotas, services,        |
repositories e ingest   |
  |                     |
  v                     |
Firebase Admin SDK -----+
  |
  +--> APIs externas de metadados academicos
       OpenAlex, ORCID, Crossref, Semantic Scholar
```

### Componentes principais

| Camada | Evidencia no projeto | Responsabilidade | Observacao SSQM |
|---|---|---|---|
| Frontend | `apresentacao/src/` | Interface web, relatorios, dashboards, CRUDs | Usa API FastAPI, mas algumas telas possuem fallback direto para RTDB. |
| Backend | `functions/main.py` | API REST, registro de rotas, agregacoes e proxies | A aplicacao e portavel como FastAPI, mas a persistencia ainda e fortemente acoplada ao Firebase. |
| Repositorios | `functions/repositories/`, `functions/common/dbref.py` | CRUD sobre nos do RTDB | Existe uma tentativa positiva de centralizar acesso ao banco. |
| Services/workers | `functions/services/`, `functions/workers/` | Regras de negocio e processamento de autores/produtos | Ainda ha acesso direto ao Firebase fora dos repositorios. |
| Ingestao | `functions/ingest/`, `functions/api_routes/harvest_authors.py` | Coleta dados externos de producao academica | Depende de disponibilidade e politicas de APIs publicas externas. |
| Infraestrutura | `firebase.json`, `.firebaserc`, `.github/workflows/` | Hosting, emulador, deploy e CI/CD | Ha drift de configuracao entre README, Firebase config e workflows. |

### Principais achados arquiteturais

- O Firebase RTDB e a dependencia mais critica: aparece no backend, em repositorios, em services e como fallback em telas do frontend.
- A camada `functions/common/dbref.py` reduz parte do acoplamento, mas nao elimina chamadas diretas a `firebase_admin.db`.
- O frontend deveria consumir somente a API, mas ainda possui URLs diretas para `*.firebaseio.com`.
- O projeto depende de APIs externas para enriquecimento bibliografico. O sistema pode continuar com dados existentes, mas a ingestao e a atualizacao automatica ficam degradadas se essas APIs falharem.
- A documentacao e os arquivos de infraestrutura estao parcialmente divergentes: `firebase.json` aponta para `public`, enquanto o README descreve `apresentacao/dist`; workflows usam `metaorganizer-project`, enquanto `.firebaserc` aponta para `poshbard`.

## 2. Inventario de Dependencias

### Tabela completa de dependencias avaliadas

| ID | Dependencia | Categoria | Provedor/ecossistema | Uso no sistema | Criticidade | Lock-in potencial | Alternativa conhecida |
|---|---|---|---|---|---|---|---|
| DEP-01 | Firebase Realtime Database | Banco cloud/BaaS | Google/Firebase | Persistencia principal dos dados | Alta | Alto | PostgreSQL, MySQL/MariaDB, SQLite sincronizado, Supabase self-hosted |
| DEP-02 | Firebase Admin SDK | SDK proprietario de acesso a dados | Google/Firebase | Acesso autenticado ao RTDB no backend | Alta | Alto | SQLAlchemy, drivers PostgreSQL, camada repository com porta/adaptador |
| DEP-03 | Google Application Default Credentials/service account | IAM/credenciais | Google Cloud | Autenticacao operacional do backend no Firebase | Alta | Alto | OIDC proprio, Vault, secrets locais, Keycloak para identidade de usuarios |
| DEP-04 | Firebase Hosting/Firebase CLI/action-hosting-deploy | Hosting e deploy | Google/Firebase/GitHub | Publicacao do frontend e preview/deploy | Media | Medio/Alto | Nginx, Caddy, Netlify, Cloudflare Pages, GitLab Pages, servidor proprio |
| DEP-05 | GitHub Actions | CI/CD | GitHub/Microsoft | Pipeline de build e deploy | Media | Baixo/Medio | GitLab CI, Jenkins, Woodpecker CI, Gitea Actions |
| DEP-06 | OpenAlex API | API externa de metadados | OpenAlex | Busca/importacao de autores, works e perfis | Alta | Medio | Snapshots OpenAlex, cache local, Crossref, OpenAIRE, importacao CSV |
| DEP-07 | ORCID API | API externa de identidade academica | ORCID | Resolucao de identificadores de autores | Media | Baixo | Dados informados manualmente, cache local, Lattes/CNPq quando aplicavel |
| DEP-08 | Crossref API | API externa de metadados | Crossref | Complemento de obras e DOI | Media | Baixo/Medio | OpenAlex, DataCite, importacao manual/CSV |
| DEP-09 | Semantic Scholar API | API externa de metadados | Semantic Scholar | Busca complementar de producao academica | Media | Medio | OpenAlex, Crossref, cache local |
| DEP-10 | FastAPI | Framework web OSS | Python ecosystem | API REST | Alta | Baixo | Flask, Litestar, Django REST Framework |
| DEP-11 | Uvicorn | Servidor ASGI OSS | Python ecosystem | Execucao da API local/servidor | Alta | Baixo | Hypercorn, Gunicorn com workers ASGI |
| DEP-12 | Pydantic/pydantic-settings | Validacao/configuracao OSS | Python ecosystem | Settings, schemas e validacao | Alta | Baixo | attrs, dataclasses, Marshmallow |
| DEP-13 | python-dotenv | Configuracao local OSS | Python ecosystem | Carregamento de `.env` | Baixa | Baixo | Variaveis de ambiente nativas, direnv |
| DEP-14 | requests | Cliente HTTP OSS | Python ecosystem | Chamadas para APIs externas | Media | Baixo | httpx, aiohttp, urllib |
| DEP-15 | React/react-dom | UI framework OSS | npm ecosystem | Frontend principal | Alta | Baixo/Medio | Vue, Svelte, Angular, Web Components |
| DEP-16 | Vite/@vitejs/plugin-react | Build tool OSS | npm ecosystem | Build e dev server do frontend | Media | Baixo | webpack, Rsbuild, Parcel |
| DEP-17 | react-router-dom | Roteamento frontend OSS | npm ecosystem | Navegacao SPA | Media | Baixo | TanStack Router, roteamento proprio |
| DEP-18 | Chart.js/react-chartjs-2/Recharts | Visualizacao OSS | npm ecosystem | Graficos e relatorios | Media | Baixo | ECharts, D3, Nivo |
| DEP-19 | Firebase JS SDK | SDK proprietario no frontend | Google/Firebase | Dependencia declarada; cliente atual esta stubado | Baixa atual, alta se reativado | Alto | Remover SDK do frontend; consumir somente API |
| DEP-20 | ESLint e plugins | Qualidade de codigo OSS | npm ecosystem | Lint do frontend | Baixa | Baixo | Biome, StandardJS |
| DEP-21 | npm registry | Supply chain | npm | Instalacao de pacotes JS | Media | Baixo/Medio | Mirror privado, pnpm store, Verdaccio |
| DEP-22 | PyPI/pip | Supply chain | Python | Instalacao de pacotes Python | Media | Baixo/Medio | Mirror privado, devpi, Artifactory |

### Dependencias por provedor/ecossistema

| Provedor/ecossistema | Quantidade | Dependencias principais | Risco SSQM |
|---|---:|---|---|
| Google/Firebase | 5 | RTDB, Admin SDK, ADC, Hosting, Firebase JS SDK | Alto, por concentrar dados, credenciais e publicacao. |
| APIs academicas externas | 4 | OpenAlex, ORCID, Crossref, Semantic Scholar | Medio, por afetar ingestao e atualizacao de dados. |
| npm/React | 7 | React, Vite, Router, graficos, lint, npm | Baixo/medio, dependencias abertas com boa substituibilidade. |
| Python/PyPI | 6 | FastAPI, Uvicorn, Pydantic, dotenv, requests, PyPI | Baixo/medio, tecnologias abertas e portaveis. |
| GitHub/Microsoft | 1 | GitHub Actions | Baixo/medio, substituivel, mas acoplado aos workflows atuais. |

## 3. Lock-In Smells Identificados

| ID | Smell | Categoria | Evidencia encontrada | Impacto | Severidade |
|---|---|---|---|---|---|
| CLS-01 | Firebase RTDB como persistencia principal | Database/Storage Lock-In | `config/firebase_admin_init.py`, `functions/repositories/base.py`, `functions/main.py` | Migrar dados e consultas exige reescrever camada de persistencia. | Critica |
| CLS-02 | SDK Firebase vazando para varias camadas | SDK/API Lock-In | `firebase_admin.db` aparece em `functions/main.py`, `functions/services/pesquisa.py`, scripts e repositorios | Regras de negocio e operacoes ficam dependentes da API proprietaria. | Alta |
| CLS-03 | Frontend com fallback direto para RTDB | Storage/API Bypass Lock-In | `VITE_RTDB_URL` e chamadas `*.firebaseio.com/*.json` em telas React | Quebra o isolamento da API e duplica o acoplamento ao banco. | Alta |
| CLS-04 | Credenciais operacionais vinculadas ao Google ADC | Identity/Operational Lock-In | README e `config/firebase_admin_init.py` exigem `GOOGLE_APPLICATION_CREDENTIALS` ou ADC | Operacao depende de modelo de identidade Google. | Alta |
| CLS-05 | Hosting e deploy acoplados ao Firebase | Infrastructure Lock-In | `firebase.json` e workflows com `FirebaseExtended/action-hosting-deploy` | A publicacao depende do ecossistema Firebase/GitHub. | Moderada |
| CLS-06 | Dependencia de APIs externas para ingestao academica | External API Lock-In | OpenAlex, ORCID, Crossref e Semantic Scholar nos modulos `functions/ingest/` | Atualizacao automatica pode parar por quota, indisponibilidade ou mudanca de API. | Moderada |
| CLS-07 | Drift de configuracao de ambientes/projetos | Governance/Configuration Smell | `.firebaserc` usa `poshbard`; workflows usam `metaorganizer-project`; README cita outro diretorio de hosting | Aumenta risco operacional e dificulta reproducibilidade. | Moderada |
| CLS-08 | Documentacao arquitetural parcialmente divergente | Knowledge/Strategic Smell | Documento interno cita ADRs e `docs/ARCHITECTURE.md`, mas esses arquivos nao aparecem no inventario atual | Reduz autonomia de novas equipes e dificulta governanca de migracao. | Moderada |
| CLS-09 | Dependencia potencial de Firebase JS SDK no frontend | Authentication/Frontend Lock-In potencial | `apresentacao/package.json` ainda declara `firebase`, embora `firebaseClient.js` esteja stubado | Se reativado sem abstracao, pode recriar lock-in no cliente. | Baixa atual |

### Classificacao por categoria

| Categoria | Quantidade | Itens |
|---|---:|---|
| Database/Storage Lock-In | 2 | CLS-01, CLS-03 |
| SDK/API Lock-In | 1 | CLS-02 |
| Identity/Operational Lock-In | 1 | CLS-04 |
| Infrastructure/DevOps Lock-In | 1 | CLS-05 |
| External API Lock-In | 1 | CLS-06 |
| Governance/Knowledge Smells | 2 | CLS-07, CLS-08 |
| Authentication/Frontend Lock-In potencial | 1 | CLS-09 |
| AI Lock-In | 0 | Nao ha dependencia de IA em producao no estado atual. |

## 4. Resultado do Checklist SSQM

Escala aplicada: `0 = nao atende`, `1 = atende parcialmente`, `2 = atende plenamente`.

| Dimensao | Pontuacao | Justificativa resumida |
|---|---:|---|
| ST - Soberania Tecnologica | 3/10 | Ha tecnologias abertas no stack, mas a persistencia e parte da operacao dependem fortemente de Firebase/Google. |
| SO - Soberania Operacional | 1/10 | O sistema nao possui contingencia clara para indisponibilidade do provedor de dados; a degradacao e limitada. |
| SD - Soberania de Dados | 2/10 | A organizacao acessa os dados via credenciais, mas nao ha rotina documentada de exportacao, backup e migracao independente. |
| SA - Soberania Arquitetural | 4/10 | Existem repositorios e `dbref`, mas ainda ha chamadas Firebase espalhadas e acesso direto do frontend ao RTDB. |
| SI - Soberania de IA | 10/10 | O sistema atual nao depende de IA externa em producao; o risco e futuro, nao atual. |
| SDV - Soberania de Desenvolvimento | 8/10 | Build local e dependencias estao documentados; CI/CD e deploy ainda dependem de GitHub/Firebase. |
| SK - Soberania de Conhecimento | 6/10 | Ha README, diagramas PlantUML e docs auxiliares, mas parte das referencias arquiteturais parece incompleta ou desatualizada. |
| SE - Soberania de Ecossistema | 3/10 | A concentracao Google/Firebase e relevante; faltam monitoramento e avaliacao periodica de dependencias. |
| SS - Soberania Estrategica | 2/10 | Ha indicios de planejamento, mas falta plano formal de migracao, estimativas e priorizacao antes deste relatorio. |

**Pontuacao total:** 39/90  
**SSQMScore:** 43,3%  
**Nivel SSQM:** Nivel 3 - Dependencia Moderada

> Observacao: a nota de IA eleva a media porque nao existe IA acoplada em producao. Isso nao deve mascarar o risco central do sistema, que esta em dados, operacao e infraestrutura Firebase.

## 5. Indices Calculados

### Criterios usados

Para tornar o calculo auditavel, foram adotadas as seguintes normalizacoes:

- **IDC - Indice de Dependencia Critica:** media do risco das 9 dependencias externas/operacionais principais. Cada risco combina criticidade e lock-in potencial.
- **CLSn - Cloud Lock-In Smells normalizados:** soma das severidades dos smells dividida pela severidade maxima possivel.
- **IP - Indice de Portabilidade:** media das notas de portabilidade das dependencias externas, em escala `1 = muito dificil` a `5 = muito facil`, normalizada por 5.
- **SSQMScore:** pontuacao do checklist dividida por 90.
- **IDAN:** media entre dependencia critica, smells, falta de portabilidade e falta de soberania:

```text
IDAN = (IDC + CLSn + (1 - IP) + (1 - SSQMScore)) / 4
```

### Resultados

| Indice | Valor | Interpretacao |
|---|---:|---|
| IDC | 0,53 | Dependencia critica media/alta, puxada por Firebase RTDB, Admin SDK, ADC e OpenAlex. |
| IP | 0,58 | Portabilidade moderada: o stack de aplicacao e portavel, mas dados e Firebase reduzem a mobilidade. |
| CLSn | 0,66 | Smells relevantes, com destaque para banco, SDK e bypass direto do frontend. |
| SSQMScore | 0,43 | Nivel 3 SSQM, dependencia moderada. |
| IDAN | 0,55 | Dependencia arquitetural em nuvem relevante, proxima da faixa de dependencia elevada. |

Pela escala do material de Cloud Lock-in Smells, `0,4 - 0,6` representa **dependencia relevante**. O valor calculado nao indica colapso de soberania, mas mostra que a autonomia operacional depende de remover primeiro os acoplamentos de dados e infraestrutura.

## 6. Arquitetura Alvo - TO-BE

A arquitetura alvo recomendada deve preservar o que o projeto ja tem de bom - FastAPI, React, organizacao em rotas/repositorios e ingestao por modulos - mas trocar dependencias proprietarias por portas/adaptadores e armazenamento mais portavel.

```text
Usuario
  |
  v
Frontend React/Vite
  |
  v
API/BFF FastAPI
  |
  +--> Application services
  |      |
  |      +--> Portas de repositorio
  |      +--> Portas de ingestao externa
  |      +--> Portas de autenticacao
  |
  +--> Adaptador PostgreSQL
  +--> Adaptador cache/filas
  +--> Adaptadores OpenAlex/ORCID/Crossref/Semantic Scholar
  +--> Exportacao/backup em formatos abertos
```

### Decisoes recomendadas para aumentar soberania

| Area | AS-IS | TO-BE recomendado | Ganho de soberania |
|---|---|---|---|
| Persistencia | Firebase RTDB | PostgreSQL como base canonica; export JSON/CSV; migrations versionadas | Reduz lock-in de dados e melhora portabilidade. |
| Acesso a dados | SDK Firebase em varias camadas | Interfaces de repositorio + adaptadores substituiveis | Permite migrar banco sem reescrever regras de negocio. |
| Frontend | API + fallback RTDB | Frontend consome somente API | Elimina acoplamento do cliente ao fornecedor de banco. |
| Ingestao | Rotas HTTP e chamadas diretas a APIs externas | Jobs/filas com cache local, retries, rate limiting e snapshots | Reduz indisponibilidade causada por APIs externas. |
| Identidade/credenciais | Google ADC/service account | Secrets independentes do provedor; opcional Keycloak para usuarios | Reduz dependencia operacional Google. |
| Deploy | Firebase Hosting + GitHub Actions | Container Docker, deploy em VPS/Kubernetes/Cloud Run ou ambiente hibrido | Aumenta reproducibilidade e poder de troca. |
| CI/CD | GitHub Actions especifico | Pipeline portavel documentado para GitHub, GitLab CI ou Jenkins | Reduz risco de plataforma unica. |
| Observabilidade | Nao evidenciada | Logs, metricas, backups testados e health checks externos | Aumenta continuidade operacional. |

## 7. Roadmap de Migracao

### Curto prazo - 0 a 6 meses

| Prioridade | Acao | Dependencias afetadas | Resultado esperado | Esforco estimado |
|---|---|---|---|---:|
| Alta | Remover chamadas diretas do frontend ao RTDB e exigir acesso via FastAPI | DEP-01, DEP-19 | Cliente desacoplado do Firebase | 24-40 h |
| Alta | Centralizar 100% do acesso Firebase em repositories/adapters | DEP-01, DEP-02 | Regras de negocio sem `firebase_admin.db` direto | 40-80 h |
| Alta | Criar exportacao versionada dos dados em JSON/CSV | DEP-01 | Saida de emergencia para dados | 24-40 h |
| Alta | Corrigir drift de configuracao (`firebase.json`, `.firebaserc`, workflows, README) | DEP-04, DEP-05 | Ambientes mais reproduziveis | 8-16 h |
| Media | Documentar mapa de nos RTDB e modelo canonico | DEP-01 | Base segura para migracao de dados | 16-32 h |
| Media | Adicionar testes para repositorios e endpoints principais | Stack backend | Reducao de risco na troca de banco | 40-80 h |
| Media | Criar camada de clientes para OpenAlex/ORCID/Crossref/S2 com cache e timeout padrao | DEP-06 a DEP-09 | Menos falhas por indisponibilidade externa | 32-64 h |

### Medio prazo - 6 a 18 meses

| Prioridade | Acao | Dependencias afetadas | Resultado esperado | Esforco estimado |
|---|---|---|---|---:|
| Alta | Implementar adaptador PostgreSQL para entidades canonicas | DEP-01, DEP-02 | Persistencia portavel | 120-220 h |
| Alta | Criar script de migracao RTDB -> PostgreSQL com validacao e rollback | DEP-01 | Migracao auditavel e repetivel | 80-160 h |
| Alta | Remover dependencia do Firebase JS SDK se continuar sem uso real | DEP-19 | Frontend mais simples e soberano | 8-16 h |
| Media | Containerizar backend e frontend com build reprodutivel | DEP-04, DEP-05 | Deploy independente de Firebase Hosting | 40-80 h |
| Media | Separar ingestao pesada em jobs/worker com fila e retries | DEP-06 a DEP-09 | Operacao mais robusta | 80-160 h |
| Media | Criar pipeline CI/CD portavel documentado | DEP-05 | Execucao em GitHub/GitLab/Jenkins | 24-48 h |
| Media | Definir estrategia de autenticacao propria, se login real for necessario | DEP-03 | Menor dependencia de identidade Google | 40-120 h |

### Longo prazo - 18 a 36 meses

| Prioridade | Acao | Dependencias afetadas | Resultado esperado | Esforco estimado |
|---|---|---|---|---:|
| Alta | Operar versao sem Firebase em ambiente proprio ou hibrido | DEP-01 a DEP-04 | Autonomia operacional elevada | 160-320 h |
| Alta | Automatizar backups, restore testado e plano de continuidade | Dados/infra | Soberania de dados e recuperacao verificavel | 80-160 h |
| Media | Manter cache/mirror local dos metadados academicos essenciais | DEP-06 a DEP-09 | Menor dependencia de APIs externas | 80-200 h |
| Media | Implantar observabilidade independente de provedor | Infra | Monitoramento e auditoria proprios | 40-120 h |
| Media | Revisar SSQM semestralmente e atualizar inventario de dependencias | Governanca | Soberania como pratica continua | 16-32 h por ciclo |

## 8. Respostas Objetivas Esperadas

### Quao dependente o sistema e de fornecedores externos?

O sistema tem **dependencia relevante** de fornecedores externos. O IDAN calculado foi **0,55**, dentro da faixa `0,4 - 0,6`. A dependencia nao e critica para todo o stack, porque FastAPI, React e as bibliotecas centrais sao abertas, mas e alta na camada de dados e operacao por causa do Firebase/Google.

### Quais sao os principais riscos de lock-in?

1. Firebase RTDB como banco principal.
2. Firebase Admin SDK usado diretamente fora de um adaptador unico.
3. Frontend acessando RTDB diretamente como fallback.
4. Credenciais e operacao vinculadas ao Google ADC/service account.
5. Deploy/hosting em Firebase com configuracao divergente.
6. Ingestao dependente de APIs externas sem cache/snapshot robusto.

### Qual o nivel atual de soberania tecnologica?

O SSQMScore e **39/90**, ou **43,3%**, classificando o projeto como **Nivel 3 - Dependencia Moderada**. A leitura qualitativa e: soberania boa no codigo-fonte e no stack aberto de aplicacao, mas soberania fraca em dados, operacao e infraestrutura.

### Quais dependencias devem ser removidas primeiro?

| Prioridade | Dependencia | Motivo |
|---|---|---|
| 1 | Acesso direto do frontend ao RTDB | E rapido de mitigar e reduz acoplamento visivel ao fornecedor. |
| 2 | Chamadas diretas `firebase_admin.db` fora dos repositorios | Prepara o sistema para trocar banco sem reescrever regras de negocio. |
| 3 | Firebase RTDB como armazenamento canonico | E o maior fator de lock-in e soberania de dados. |
| 4 | Firebase Hosting/deploy especifico | Menos critico que dados, mas importante para autonomia operacional. |
| 5 | Dependencia sem cache das APIs academicas externas | Afeta continuidade da ingestao e confiabilidade dos relatorios. |

### Qual arquitetura futura aumenta a autonomia operacional?

A arquitetura alvo mais adequada e uma **API FastAPI com portas/adaptadores**, frontend consumindo somente a API, banco canonico PostgreSQL, jobs de ingestao desacoplados e deploy containerizado. Firebase pode permanecer temporariamente como adaptador legado durante a migracao, mas nao deve continuar como modelo de dominio nem como canal direto do frontend.

### Qual o esforco estimado para alcancar maior soberania digital?

Para sair de dependencia moderada/relevante para autonomia parcial ou alta, o esforco estimado e:

| Horizonte | Esforco aproximado | Objetivo |
|---|---:|---|
| 0-6 meses | 184-352 h | Reduzir acoplamentos diretos, corrigir configuracoes, criar exportacao e testes. |
| 6-18 meses | 392-764 h | Migrar persistencia canonica, containerizar e tornar CI/CD portavel. |
| 18-36 meses | 376-832 h | Operar sem Firebase, fortalecer continuidade, observabilidade e governanca SSQM. |

**Estimativa total:** 952-1.948 horas, variando conforme volume real de dados, cobertura de testes desejada e nivel de automacao exigido.

## 9. Conclusao

O Poshboard nao esta preso por toda a sua tecnologia: linguagem, framework backend, frontend e bibliotecas principais sao majoritariamente abertas e substituiveis. O problema central de soberania esta na **concentracao de dados, credenciais e operacao em Firebase/Google**, somada a acessos diretos ao RTDB no backend e no frontend.

A primeira meta de evolucao deve ser reduzir o acoplamento antes de trocar a infraestrutura. Em termos praticos: remover o RTDB do frontend, encapsular Firebase em adaptadores, criar exportacao de dados e preparar PostgreSQL como persistencia canonica. Esse caminho aumenta a autonomia sem exigir uma reescrita completa do sistema.
