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
| `functions/ingest/openalex.py` | editado | #9 | `import requests` removido; usa `http_client.get` |
| `tests/test_storage_contract.py` | **novo** | #10 | Contrato parametrizado: 14 casos × 2 backends |
| `tests/test_http_client.py` | **novo** | #10 | 7 casos unitários do cliente HTTP |
| `functions/main.py` | editado | #11, #15 | Removido print Google ADC; aviso se credencial desnecessária; health check com verificação real de DB |
| `.env.example` | editado | #11 | Padrão trocado para postgres; variáveis Firebase comentadas |
| `.github/workflows/ci.yml` | **novo** | #13 | Pipeline pytest + docker build + npm build sem Firebase |
| `requirements.txt` | editado | — | `psycopg[binary]>=3.2.10` (versão 3.2.3 foi descontinuada) |

## Resultado dos testes

```
43 passed in 2.02s
```

- `test_storage_contract.py` — 28 cases (14 cenários × firebase_fake + postgres_sqlite)
- `test_http_client.py` — 7 cases
- `test_postgres_adapter.py` — 8 cases (pré-existentes, continuam passando)
