# Issues SSQM implementadas — 2026-06-22

---

## #6 — Portar queries RTDB para o StoragePort (dívida)

### Por que foi feito
O `DocenteCRUD.find_by_orcid` precisava buscar um docente pelo campo ORCID. Para isso, usava `self.ref()` — um "escape hatch" que retornava uma referência direta ao Firebase RTDB e chamava `order_by_child("orcid").equal_to(orcid)`, que é uma API exclusiva do Firebase Admin SDK. Isso criava uma dependência oculta: o método **só funcionava com o backend Firebase**. Ao trocar para `STORAGE_BACKEND=postgres`, a chamada lançava `NotImplementedError` em tempo de execução.

### O que foi ajustado e por quê

**`functions/repositories/ports.py`**
Havia apenas 5 métodos no protocolo `StoragePort` (create, list, get, update, delete). Não existia nenhum método para busca por campo — a lacuna forçava qualquer query do tipo "buscar por valor de campo" a usar o escape hatch `self.ref()`, que vaza para a camada Firebase.
→ Adicionado `find_by_field(path_root, field, value)` ao protocolo. Agora qualquer adaptador que implemente a porta precisa oferecer essa operação. Nenhuma query de domínio precisa mais chamar a API Firebase diretamente.

**`functions/adapters/firebase_adapter.py`**
O adaptador não implementava `find_by_field`. Sem ele, o único jeito de buscar por campo era chamar `raw_ref()` de fora do adaptador, espalhando código Firebase pelo domínio.
→ Implementado `find_by_field` usando `order_by_child(field).equal_to(value).get()` — a chamada Firebase fica **dentro** do adaptador, que é o único lugar onde ela pode aparecer.

**`functions/adapters/postgres_adapter.py`**
Mesma ausência: não havia implementação de busca por campo. Com Postgres, a operação precisa ser feita em SQL — mas o domínio não pode saber disso.
→ Implementado `find_by_field` com uma query SQLAlchemy que carrega todos os documentos da coleção e filtra em Python por `data.get(field) == value`. Funciona igual no SQLite (testes) e no PostgreSQL (produção).

**`functions/repositories/docente_crud.py`**
`find_by_orcid` tinha dependência direta do Firebase: chamava `self.ref()` que retornava um objeto `firebase_admin.db.Reference` e depois chamava `.order_by_child().equal_to()`. Esse código não funcionava em nenhum outro backend.
→ Substituído por `self.storage.find_by_field(self.path_root, "orcid", orcid)`. Agora o método delega para a porta, que roteia para o adaptador correto (Firebase ou Postgres) sem que o CRUD precise saber qual está ativo. A dependência com o Firebase Admin SDK foi removida deste arquivo.

---

## #9 — Camada de clientes externos com cache, timeout e retry (CLS-06)

### Por que foi feito
Os módulos de ingestão buscam dados de 4 APIs externas acadêmicas: OpenAlex, ORCID, Crossref e Semantic Scholar. Cada um fazia chamadas `requests.get()` de forma independente, sem padronização. Isso criava 3 problemas: (1) uma falha de rede pontual derrubava o fluxo inteiro sem nova tentativa; (2) a mesma URL podia ser chamada várias vezes em sequência sem reaproveitar a resposta; (3) timeouts diferentes entre módulos tornavam o comportamento imprevisível.

### O que foi ajustado e por quê

**`functions/common/http_client.py` (arquivo novo)**
Não existia nenhuma camada compartilhada de HTTP. Cada módulo importava `requests` diretamente e definia seu próprio timeout e tratamento de erro.
→ Criado cliente unificado com: cache em memória com TTL configurável (padrão 5 min, evita bater na mesma API desnecessariamente), retry com backoff exponencial (padrão 3 tentativas, fator 1.5× entre elas, só para erros de rede — erros 4xx não são retentados pois são definitivos), e timeout configurável por chamada. Todos os módulos de ingestão agora dependem deste arquivo, não de `requests` diretamente.

**`functions/ingest/crossref_api.py`**
Tinha `import requests` e chamava `requests.get(url, ..., timeout=25)` diretamente. Se a Crossref retornasse erro de rede, o endpoint FastAPI falhava imediatamente sem nova tentativa.
→ Removido `import requests`. Substituída a chamada por `http_client.get(...)`. A dependência com `requests` saiu deste arquivo — ele agora depende só do cliente interno, que encapsula retry e cache.

**`functions/ingest/orcid_api.py`**
Mesma situação: `import requests` direto, sem retry. Adicionalmente, a verificação de status HTTP era manual (`if r.status_code == 404`), diferente do padrão dos outros módulos.
→ Removido `import requests`. Chamada substituída por `http_client.get(...)`. O tratamento de 404 foi mantido, mas agora inspeciona a exceção `HTTPError` levantada pelo cliente, seguindo o mesmo padrão dos demais módulos.

**`functions/ingest/semanticscholar_api.py`**
Tinha duas funções (`s2_author_search` e `s2_author`) com `requests.get` cada uma, com verificações de status duplicadas.
→ Removido `import requests`. As duas funções agora usam `http_client.get(...)`. A verificação de 404 foi unificada no padrão de inspeção de `HTTPError`.

**`functions/ingest/openalex.py`**
Diferente dos outros: chamava `requests.get` dentro de um loop de paginação por cursor. A cada iteração, um erro de rede abortava a ingestão inteira — mesmo que só uma página de 200 tivesse falhado.
→ Removido `import requests`. Substituída por `http_client.get(..., cache_ttl=0)` — TTL zero porque cada página de cursor é única e não deve ser cacheada. O retry agora funciona por página: se uma falhar transitoriamente, o cliente retenta antes de propagar o erro.

---

## #10 — Cobertura de testes (contrato StoragePort + cliente HTTP)

### Por que foi feito
Os testes existentes cobriam o `PostgresAdapter` de forma isolada (`test_postgres_adapter.py`), mas não havia nenhum teste que garantisse que `FirebaseRTDBAdapter` e `PostgresAdapter` se comportavam de forma idêntica para as mesmas operações. Isso significava que um adaptador poderia divergir do outro sem que nenhum teste detectasse — só apareceria em produção ao trocar o backend.

### O que foi ajustado e por quê

**`tests/test_storage_contract.py` (arquivo novo)**
Não existia teste de contrato. Para testar o `FirebaseRTDBAdapter` sem credenciais reais, era necessário um "fake" em memória que imitasse a API do Firebase (push/child/set/get/order_by_child). Para testar o `PostgresAdapter` sem servidor, era necessário SQLite em memória.
→ Criado arquivo com `FakeFirebaseAdapter` (implementa as operações de RTDB em memória pura) e fixture parametrizada que roda os mesmos 14 casos de teste contra os dois adaptadores. Qualquer divergência de comportamento aparece como falha de teste antes de chegar em produção. Os 3 cenários de `find_by_field` (adicionado na issue #6) também estão cobertos nos dois backends.

**`tests/test_http_client.py` (arquivo novo)**
O `http_client.py` criado na issue #9 não tinha nenhum teste. Sem testes, não seria possível verificar se o retry realmente acontecia, se o cache estava funcionando ou se erros 4xx eram tratados diferente de erros de rede.
→ Criado arquivo com 7 casos usando `unittest.mock.patch` para simular `requests.get` sem tocar na rede. Cobrem: resposta de sucesso, cache hit (segunda chamada não faz requisição), cache desativado com TTL zero, retry em Timeout, retry em ConnectionError, não-retry em HTTPError 4xx, e sucesso na segunda tentativa após falha.

---

## #11 — Credenciais independentes do Google ADC (CLS-04)

### Por que foi feito
A aplicação já inicializava o Firebase condicionalmente (`if STORAGE_BACKEND == "firebase"`), mas havia dois problemas práticos: o `.env.example` listava `GOOGLE_APPLICATION_CREDENTIALS` como variável necessária (sem dizer que era só para Firebase), e o `main.py` imprimia o path da credencial Google no terminal toda vez que a app subia — mesmo com `STORAGE_BACKEND=postgres`, quando a credencial não é usada. Isso gerava confusão: novos desenvolvedores não conseguiam subir a app com Postgres sem procurar um arquivo de service account.

### O que foi ajustado e por quê

**`functions/main.py`**
Tinha `print("Firebase cred path:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))` na linha 12, executado incondicionalmente — mesmo com backend Postgres, mesmo sem nenhum Firebase ativo. Além disso, não havia nenhum aviso caso a variável estivesse definida sem ser necessária.
→ Removido o `print`. Adicionado `warnings.warn` que só dispara se `GOOGLE_APPLICATION_CREDENTIALS` estiver definida **com** `STORAGE_BACKEND=postgres` — ou seja, avisa que a credencial não será usada e pode ser removida do ambiente. Com isso, o startup no modo Postgres não menciona nada relacionado ao Google.

**`.env.example`**
Estava com `STORAGE_BACKEND=firebase` como padrão e `GOOGLE_APPLICATION_CREDENTIALS=./service-account.json` como linha ativa (não comentada), passando a impressão de que ambas eram obrigatórias independente do backend.
→ Padrão trocado para `STORAGE_BACKEND=postgres`. As variáveis Firebase (`PROJECT_ID`, `RTDB_URL`, `GOOGLE_APPLICATION_CREDENTIALS`) foram comentadas com a nota *"necessário APENAS com STORAGE_BACKEND=firebase — com postgres podem ser omitidas"*. Agora um desenvolvedor novo consegue subir o projeto com `docker-compose up` sem precisar de nenhuma credencial Google.

---

## #13 — Pipeline CI/CD portável (CLS-05)

### Por que foi feito
Os dois workflows existentes (`firebase-hosting-merge.yml` e `firebase-hosting-pull-request.yml`) foram gerados automaticamente pelo Firebase CLI e faziam apenas uma coisa: deploy no Firebase Hosting usando `FIREBASE_SERVICE_ACCOUNT_METAORGANIZER_PROJECT` como segredo. Não rodavam nenhum teste, não validavam a build da imagem Docker, não verificavam o frontend. Qualquer push na `main` podia quebrar a aplicação sem nenhum aviso.

### O que foi ajustado e por quê

**`.github/workflows/ci.yml` (arquivo novo)**
Não existia nenhum pipeline de integração contínua. Os workflows antigos dependiam do segredo `FIREBASE_SERVICE_ACCOUNT_METAORGANIZER_PROJECT` — sem ele, não funcionavam. Um repositório sem Firebase não poderia rodar nenhum CI com esses arquivos.
→ Criado pipeline com 3 jobs independentes:
- `test`: instala dependências Python, roda `pytest` com `STORAGE_BACKEND=postgres` e `DATABASE_URL=sqlite+pysqlite:///:memory:` — sem servidor externo, sem credencial Firebase, sem credencial Google. Qualquer falha de teste bloqueia o job seguinte.
- `build-image`: só roda se `test` passar (`needs: test`). Executa `docker build -f Dockerfile.backend` para validar que a imagem do backend constrói sem erro.
- `build-frontend`: roda em paralelo com `test`. Executa `npm ci && npm run build` na pasta `apresentacao` para garantir que o frontend compila.

Os workflows antigos do Firebase foram mantidos no repositório (não removidos) para não quebrar deployments existentes, mas o novo `ci.yml` passa a ser o ponto central de validação.

---

## #15 — Health check robusto + operação sem Firebase

### Por que foi feito
O endpoint `GET /health` retornava sempre `{"ok": true}` com HTTP 200, independente do estado real do banco. Com `STORAGE_BACKEND=postgres`, se o PostgreSQL estivesse fora do ar (container reiniciando, falha de rede, senha errada), o health check continuava verde. Qualquer orquestrador (Docker Compose `healthcheck`, Kubernetes `livenessProbe`, load balancer) entendia o serviço como saudável quando não estava, e não tomava nenhuma ação corretiva.

### O que foi ajustado e por quê

**`functions/main.py` — endpoint `/health`**
Tinha apenas `return {"ok": True}` — sem nenhuma verificação real. A resposta era estática e não refletia o estado do sistema.
→ Com `STORAGE_BACKEND=postgres`, o endpoint agora chama `storage.list("_health_check")` — uma leitura real ao banco, na coleção sentinel `_health_check` (que pode estar vazia, o que é normal). Se a conexão estiver saudável, retorna HTTP 200 com `{"ok": true, "backend": "postgres", "db": "ok"}`. Se a conexão falhar, retorna HTTP 503 com `{"detail": {"backend": "postgres", "db": "error: <mensagem>"}}`, que o orquestrador interpreta como serviço indisponível e pode agir (reiniciar, remover do balanceador, esperar). Com `STORAGE_BACKEND=firebase`, o comportamento anterior é mantido — sem verificação adicional, pois o Firebase gerencia sua própria disponibilidade.

---

## Resumo de arquivos alterados

| Arquivo | Tipo | Issue | O que mudou |
|---|---|---|---|
| `functions/repositories/ports.py` | editado | #6 | Adicionado `find_by_field` ao protocolo StoragePort |
| `functions/adapters/firebase_adapter.py` | editado | #6 | Implementado `find_by_field` usando `order_by_child` |
| `functions/adapters/postgres_adapter.py` | editado | #6 | Implementado `find_by_field` com query SQLAlchemy |
| `functions/repositories/docente_crud.py` | editado | #6 | `find_by_orcid` usa StoragePort; `self.ref()` removido |
| `functions/common/http_client.py` | **novo** | #9 | Cliente HTTP com retry/backoff/cache/timeout |
| `functions/ingest/crossref_api.py` | editado | #9 | `import requests` removido; usa `http_client.get` |
| `functions/ingest/orcid_api.py` | editado | #9 | `import requests` removido; usa `http_client.get` |
| `functions/ingest/semanticscholar_api.py` | editado | #9 | `import requests` removido; usa `http_client.get` |
| `functions/ingest/openalex.py` | editado | #9, #17 | `import requests` removido; usa `http_client.get`; cache implementado |
| `tests/test_storage_contract.py` | **novo** | #10 | Contrato parametrizado: 14 casos × 2 backends |
| `tests/test_http_client.py` | **novo** | #10 | 7 casos unitários do cliente HTTP |
| `functions/main.py` | editado | #11, #15 | Removido print Google ADC; aviso se credencial desnecessária; health check com verificação real de DB |
| `.env.example` | editado | #11 | Padrão trocado para postgres; variáveis Firebase comentadas |
| `.github/workflows/ci.yml` | **novo** | #13 | Pipeline pytest + docker build + npm build sem Firebase |
| `requirements.txt` | editado | — | `psycopg[binary]>=3.2.10` (versão 3.2.3 foi descontinuada) |
| `scripts/backup_postgres.sh` | **novo** | #16 | Script de backup automatizado com validação |
| `scripts/restore_postgres.sh` | **novo** | #16 | Script de restore com confirmação e backup de segurança |
| `scripts/test_restore.sh` | **novo** | #16 | Teste automatizado de restore semanal |
| `docs/PLANO-CONTINUIDADE.md` | **novo** | #16 | Plano completo de recuperação de desastres |
| `functions/common/metadata_cache.py` | **novo** | #17 | Cache/mirror de metadados com TTL e fallback |
| `functions/workers/incremental_update.py` | **novo** | #17 | Worker de atualização incremental |
| `docs/OBSERVABILIDADE.md` | **novo** | #18 | Documentação de logs, métricas, health checks, dashboards |
| `docs/ARCHITECTURE.md` | editado | #19 | Atualizado com arquitetura Ports/Adapters real |
| `docs/ADR-INDEX.md` | **novo** | #19 | Índice de Architectural Decision Records |
| `docs/CHECKLIST-REVISAO-SSQM.md` | **novo** | #20 | Checklist de revisão semestral do SSQM |

## Resultado dos testes

```
43 passed in 2.02s
```

- `test_storage_contract.py` — 28 cases (14 cenários × firebase_fake + postgres_sqlite)
- `test_http_client.py` — 7 cases
- `test_postgres_adapter.py` — 8 cases (pré-existentes, continuam passando)

---

## #16 — Backups automatizados, restore testado e plano de continuidade     -LEO

### Por que foi feito
Com a migração para PostgreSQL (`STORAGE_BACKEND=postgres`), tornou-se crítica a implementação de uma estratégia de backups automatizados, testes de restore e um plano de continuidade de negócios. Sem backups, qualquer falha de hardware, corrupção de dados ou erro operacional resultaria em perda total de dados. O SSQM identificou isso como prioridade máxima (Nível 3 de soberania).

### O que foi ajustado e porquê

**`scripts/backup_postgres.sh` (arquivo novo)**
Não existia nenhum script de backup automatizado. Backups manuais eram propensos a erro humano e esquecimento.
→ Criado script com: (1) dumps versionados com timestamp, (2) compressão gzip, (3) validação automática (arquivo > 0 bytes), (4) cleanup automático (30 dias), (5) suporte a execução local ou via Docker.

**`scripts/restore_postgres.sh` (arquivo novo)**
Não existia procedimento documentado ou automatizado de restore. Em um incidente real, o tempo de recuperação seria imprevisível.
→ Criado script com: (1) validação de integridade do backup (gzip test), (2) confirmação antes de destruir dados (ou --force), (3) backup de segurança do estado atual antes do restore, (4) verificação pós-restore (contagem de tabelas), (5) opção --dry-run para testes sem destruição.

**`scripts/test_restore.sh` (arquivo novo)**
Backups não testados são uma falsa sensação de segurança. Sem testes periódicos, não há garantia de que o restore funcionaria em produção.
→ Criado script que: (1) pega o backup mais recente, (2) restaura em banco isolado (`poshboard_test_restore`), (3) verifica integridade (contagem de tabelas), (4) remove banco de teste. Projetado para rodar semanalmente via cron.

**`docs/PLANO-CONTINUIDADE.md` (arquivo novo)**
Não existia documentação formal de procedimentos de recuperação de desastres. Em uma emergência, a equipe perderia tempo valioso descobrindo o que fazer.
→ Criado documento com: (1) estratégia de backup (frequência, retenção, localização), (2) procedimentos de recuperação (RTO/RPO definidos), (3) matriz de dependências críticas, (4) health checks e monitoramento, (5) contatos de emergência, (6) histórico de testes de DR.

**Cron jobs automatizados**
- Backup diário às 2h: `0 2 * * *` → `scripts/backup_postgres.sh`
- Teste semanal domingo 3h: `0 3 * * 0` → `scripts/test_restore.sh`

---

## #17 — Cache/mirror local dos metadados acadêmicos essenciais (CLS-06)

### Por que foi feito
O sistema depende de 4 APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar) para ingestão de dados acadêmicos. Isso criava 3 problemas: (1) indisponibilidade de qualquer API bloqueava a ingestão, (2) rate limits e quotas podiam ser excedidos, (3) latência alta em chamadas repetidas. O smell CLS-06 identificou essa dependência externa crítica.

### O que foi ajustado e porquê

**`functions/common/metadata_cache.py` (arquivo novo)**
Não existia nenhuma camada de cache de metadados. Cada chamada à API externa era feita do zero, sem reaproveitamento.
→ Criado módulo com: (1) cache no próprio StoragePort (Firebase ou Postgres), (2) TTL diferenciado por tipo (autor: 7 dias, obra: 30 dias, instituição: 30 dias), (3) API `get_or_fetch()` (cache-first com fallback para API), (4) funções de cleanup de expirados, (5) endpoints de gestão (`/metadata-cache/stats`, `/metadata-cache/{entity_type}`, `/metadata-cache/{entity_type}/expired`).

**`functions/workers/incremental_update.py` (arquivo novo)**
O cache, uma vez populado, nunca era atualizado. Metadados expirados permaneciam obsoletos indefinidamente.
→ Criado worker com: (1) varredura periódica de entradas expiradas, (2) atualização incremental das APIs, (3) fallback para cache expirado se API falhar (melhor que nada), (4) função `warm_up_cache()` para pós-deploy, (5) endpoints de trigger manual (`/workers/incremental-update/run`, `/warm-up`).

**`functions/ingest/openalex.py` (editado)**
A ingestão de obras do OpenAlex não usava cache. Mesmo buscas idênticas (ex.: "machine learning" com mesmos filtros) eram feitas repetidamente.
→ Adicionado parâmetro `use_cache: bool` (default True). Quando True: (1) hash dos parâmetros de busca como chave de cache, (2) TTL curto para buscas (5 min), (3) fallback para cache expirado (30 dias) se API falhar, (4) response inclui `from_cache: int` (quantos items vieram do cache).

**`functions/main.py` (editado)**
Os novos routers não estavam registrados na aplicação.
→ Adicionado imports e registro de `metadata_cache.router` e `incremental_update.router`.

**Cron job automatizado**
- Atualização incremental diária às 2h: `0 2 * * *` → `/workers/incremental-update/run` (via API)

---

## #18 — Observabilidade independente de provedor

### Por que foi feito
O sistema dependia delogs e métricas atrelados a provedores cloud (Firebase, Google Cloud). Isso criava lock-in e dificultava debug em ambiente local ou multi-cloud. O SSQM exigia observabilidade própria, independente devendor.

### O que foi ajustado e porquê

**`docs/OBSERVABILIDADE.md` (arquivo novo)**
Não existia documentação unificada sobre logs, métricas e health checks. Cada desenvolvedor implementava observabilidade de forma inconsistente.
→ Criado documento com: (1) padrão de logs estruturados (JSON), (2) descrição de endpoints de health (`/health` com verificação real de DB), (3) métricas expostas (`/metadata-cache/stats`), (4) dashboards recomendados (Grafana), (5) alertas críticos (DB down, backup falhou, etc), (6) ferramentas self-hosted (Loki, Promtail, Uptime Kuma), (7) exemplos de middleware (correlation ID, log de requests).

**Health check robusto (`/health`)**
Já implementado na Issue #15, agora documentado como parte da observabilidade.
→ Com `STORAGE_BACKEND=postgres`, chama `storage.list("_health_check")` (leitura real). HTTP 200 se saudável, 503 se DB indisponível.

---

## #19 — Alinhar documentação arquitetural e ADRs (CLS-08)

### Por que foi feito
O documento `ARCHITECTURE.md` mencionava ADRs que não existiam no inventário. Havia documentação desalinhada com a arquitetura real implementada (Ports/Adapters). O smell CLS-08 identificou Knowledge/Strategic drift.

### O que foi ajustado e porquê

**`docs/ARCHITECTURE.md` (editado)**
Estava desatualizado com a arquitetura de Ports/Adapters implementada. Citava Firestore como destino (não implementado), não mencionava PostgreSQL ou StoragePort.
→ Atualizado com: (1) status atual (Ports/Adapters com PostgreSQL + Firebase), (2) estrutura de pastas real (adapters/, repositories/ como porta), (3) descrição correta das camadas, (4) remoção de referências a Firestore, (5) data de última atualização.

**`docs/ADR-INDEX.md` (arquivo novo)**
Não existia um índice centralizado de ADRs. Os ADRs em `docs/adr/` estavam dispersos sem catalogação.
→ Criado documento com: (1) tabela de todos os ADRs (0001-0006 + novos), (2) template para novos ADRs, (3) mapeamento com smells SSQM, (4) links para todos os ADRs existentes.

**ADR-INDEX inclui**:
- 0001: Firestore em vez de RTDB (parcialmente implementado)
- 0002: Manutenção sem reengenharia
- 0003: Cloud Run em vez de Firebase Functions
- 0004: Modelo Raw e Canonical
- 0005: Handlers síncronos como dívida técnica
- 0006: Correção do drift de configuração (CLS-07)

---

## #20 — Revisão semestral do SSQM e inventário de dependências

### Por que foi feito
A soberania não pode ser um esforço pontual. Sem revisão periódica, dependências se acumulam, documentation drift ocorre, e o SSQMScore degrada. Era necessário institucionalizar a prática de governança contínua.

### O que foi ajustado e porquê

**`docs/CHECKLIST-REVISAO-SSQM.md` (arquivo novo)**
Não existia processo formal de revisão de soberania. Não havia baseline de SSQMScore para comparação futura.
→ Criado checklist detalhado com: (1) inventário de dependências (DEP-xx), (2) reavaliação de smells (CLS-xx), (3) cálculo de SSQMScore (baseline: 43.3% → Nível 3, pós-issue: 75.5% → Nível 4 em progresso), (4) métricas de backup/DR, (5) roadmap de iniciativas, (6) histórico de revisões, (7) template de aprovação.

**SSQMScore — Dimensões e Cálculo**:
- Soberania de Dados (25%): 80 — Backups automatizados, restore testado
- Portabilidade (20%): 90 — StoragePort, Docker, zero vendor lock-in
- Observabilidade (15%): 60 — Health checks OK, falta dashboards
- Resiliência (20%): 75 — Cache, retry, falta circuit breaker
- Documentação (10%): 85 — ADRs, docs atualizados
- Governança (10%): 50 — Revisão implementada, falta histórico

**Cronograma**:
- Revisão semestral (junho e dezembro)
- Duração: 16-32 horas
- Responsáveis: Tech Lead + 1 membro da equipe

---

## Cron Jobs Criados

| Nome | Schedule | Ação | Job ID |
|---|---|---|---|
| Backup diário PostgreSQL | `0 2 * * *` | Executa `scripts/backup_postgres.sh` | `43f9a32fbaba` |
| Teste semanal de restore | `0 3 * * 0` | Executa `scripts/test_restore.sh` | `6aca81f2be2a` |
| Atualização incremental do cache | `0 2 * * *` | Chama `/workers/incremental-update/run` | `42c3cd67bedf` |
