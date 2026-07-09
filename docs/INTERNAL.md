# Documentação interna para contribuidores do projeto RPV (Poshboard)

## Setup do Projeto

Siga as instruções no `README.md` para setup básico.

##bulk_ingest.py
# Workflow de Ingestão de Dados

### Chamando APIs Acadêmicas

Todas as APIs externas (OpenAlex, ORCID, Crossref, Semantic Scholar) usam o cliente HTTP unificado em `functions/common/http_client.py`.

**Exemplo:**
```python
rom functions.common import http_client

data = http_client.get(
    "https://api.openalex.org/works",
    params={"search": "machine learning"},
    timeout=30,
    cache_ttl=300  # 5 minutos de cache
)
```

### Cache de Metadados

O cache local de metadados reside em functions/common/metadata_cache.py.

**Por que usar:**
- Reduz dependência de APIs externas
- Fornece fallback quando APIs estão indisponíveis
- Acelera desenvolvimento e testes

**API:**
```python
from functions.common import metadata_cache

# Buscar do cache ou API
result = metadata_cache.get_or_fetch(
    source=" OPENALEX",
    identifier="W1234567890",
    entity_type="obra",
    fetch_fn=lambda id: http_client.get(f"https://api.openalex.org/works/{id}")
)

#result['data'] contém os metadados
# result['source'] indica se veio de 'cache' ou 'api'
```

### Tabelas de TTL por Tipo

| Tipo | TTL Padrão |
|---|---|
| autor | 7 dias |
| obra | 30 dias |
| instituicao | 30 dias |

## Testes

### Rodando Testes
```bash
pip install -r requirements-dev.txt
pytest
```

### Testes de Contrato
Os adaptadores FirebaseRTDB e Postgres share o mesmo contrato (StoragePort).
Testes em `tests/test_storage_contract.py`.

### Testes de Cliente HTTP
Testes de retry, cache e tratamento de erro em `tests/test_http_client.py`.

## Troubleshooting

### Erro: `DefaultCredentialsError`
Ocorre quando `STORAGE_BACKEND=firebase` sem credenciais Google configuridas.

**Solução:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=./path/to/service-account.json
```

Ou mude para postgres:
```
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/db
```

### Erro: CORS no frontend
Se o frontend não consegue chamar a API, defina no `.env`:
```
CORS_ORIGINS=http://localhost:5173,https://seu-dominio.com
```

### Health Check Falhando
Com `STORAGE_BACKEND=postgres`, o `/health` verifica conexão real com o banco.

**Debug:**
```bash
curl http://localhost:8000/health
# Se 503: verifique DATABASE_URL e se PostgreSQL está rodando
```

## Arquitetura

Ver `docs/ARCHITECTURE.md` para detalhes de portas/adaptadores.

Variáveis de Ambiente Críticas

| Variável | Necessário | Descrição |
|---|---|---|
|`STORAGE_BACKEND`| Não | `firebase` (default) ou `postgres` |
| `DATABASE_URL` | Sim (se postgres) | URL de conexão PostgreSQL |
| `PROJECT_ID` | Sim (se firebase) | Project ID do Firebase |
| `RTDB_URL` | Sim (se firebase) | URL do Realtime Database |
| `GOOGLE_APPLICATION_CREDENTIALS` | Opcional | Path para service account JSON |
| `CORS_ORIGINS` | Não | Origens permitidas para CORS |


O projeto implementa Web Scraping via agentes de IA para busca de currículos Lattes.

A ingestão de dados académicos é feita de forma incremental com cache.

\`\`\`