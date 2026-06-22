#docs/OBSERVABILIDADE.md

# Observabilidade Independente de Provedor

## Visão Geral
Este documento descreve a implementação de logs, métricas e health checks próprios do sistema, independentes de provedores cloud (Google, Firebase, etc.).

---

## 1. Logs Estruturados

### 1.1 Configuração de Logging
Os logs são configurados no `functions/main.py` e seguem o padrão estruturado JSON para fácil parsing por ferramentas como Loki, ELK, ou Datadog.

**Exemplo de log estruturado:**
```json
{
  "timestamp": "2026-06-22T16:00:00Z",
  "level": "INFO",
  "message": "Backup completado",
  "context": {
    "backup_file": "backup_poshboard_20260622_020000.sql.gz",
    "size_mb": 45.2
  }
}
```

### 1.2 Níveis de Log
- **DEBUG**: Detalhes de execução interna (cache hits, queries SQL)
- **INFO**: Eventos normais de operação (requests, backups, ingestões)
- **WARNING**: Situações recuperáveis (API externa falhou, cache expirado)
- **ERROR**: Falhas que requerem atenção (DB indisponível, validação falhou)

### 1.3 Coleta de Logs (Produção)
```yaml
# docker-compose. yml - adicionar Loki
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
  
  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
    command: -config.file=/etc/promtail/config.yml
```

---

## 2. Métricas e Health Checks

### 2.1 Endpoints de Saúde

#### `/health` (já implementado)
- **Método**: GET
- **Retorno**: HTTP 200 (saudável) ou 503 (indisponível)
- **Verifica**:
  - Com `STORAGE_BACKEND=postgres`: conexão real com banco via `storage.list("_health_check")`
  - Com `STORAGE_BACKEND=firebase`: sempre retorna 200 (sem verificação adicional)

**Exemplo de response:**
```json
{
  "ok": true,
  "backend": "postgres",
  "db": "ok"
}
```

**Exemplo de erro:**
```json
{
  "ok": false,
  "backend": "postgres",
  "db": "error: could not connect to server"
}
```

### 2.2 Métricas Expostas
O sistema expõe métricas operacionais via API:

#### GET `/metadata-cache/stats`
```json
{
  "autor": {"count": 150},
  "obra": {"count": 3200},
  "instituicao": {"count": 45}
}
```

#### GET `/ingest/openalex` (provenance)
- Retorna histórico de ingestões
- Include contagem de items, source, parâmetros, timestamp

### 2.3 Prometheus (Opcional)
Para integração com Prometheus, adicionar endpoint `/metrics`:
```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

## 3. Dashboards e Alertas

### 3.1 Dashboards Recomendados (Grafana)

#### Dashboard 1: Visão Geral
- Requests por minuto (últimos 30 min)
- Latência média (p50, p95, p99)
- Taxa de erro (5xx responses)
- Health check status (up/down)

#### Dashboard 2: Banco de Dados
- Conexões ativas
- Queries por segundo
- Latência de queries
- Tamanho do banco

#### Dashboard 3: Ingestão
- Items ingeridos por dia
- Sucesso vs falhas de ingestão
- Cache hit rate
- APIs externas (status, latency)

#### Dashboard 4: Cache
- Entradas por tipo (autor, obra, instituição)
- Taxa de expiração
- Atualizações incrementais

### 3.2 Alertas Críticos

| Alerta | Condição | Ação |
|---|---|---|
| **Database Down**| `/health` retorna 503 | PagerDuty/Slack imediato |
| **Backup Falhou** | Exit code != 0 no backup diário | Slack next-business-day |
| **Teste Restore Falhou** | `test_restore.sh` falha semanal | Slack + ticket |
| **API Externa Indisponível** | OpenAlex/ORCID > 5 falhas em 10 min | Log warning |
| **Cache Hit Rate < 50%** | Métrica de cache < 0.5 | Slack (otimização) |
| **Disco > 80%** | Espaço livre < 20% | Slack (cleanup) |

### 3.3 Configuração de Alerta (Exemplo Grafana)
```json
{
  "alert": {
    "name": "Health Check Failed",
    "conditions": [{
      "evaluator": {"type": "lt", "params": [1]},
      "reducer": {"type": "last"},
      "query": {"params": ["A", "5m", "now"]}
    }],
    "frequency": "1m",
    "notifications": ["slack-channel-id"]
  }
}
```

---

## 4. Monitoramento Independente

### 4.1 Health Checks Externos
Configurar monitors externos (independentes da aplicação):

#### Uptime Kuma (self-hosted)
```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    ports:
      - "3001:3001"
    volumes:
      - kuma-data:/app/data

volumes:
  kuma-data:
```

**Monitors sugeridos:**
- HTTP `GET /health` a cada 30 segundos
- HTTP `GET /` (API root) a cada 1 minuto
- TCP porta 5432 (PostgreSQL) a cada 1 minuto

### 4.2 Synthetic Monitoring
Script de monitoramento sintético:
```bash
#!/bin/bash
# scripts/synthetic_monitor.sh

API_URL="${API_URL:-http://localhost:8000}"

# Test 1: Health check
if curl -sf "$API_URL/health" > /dev/null; then
    echo "✓ Health check OK"
else
    echo "✗ Health check FAILED"
    exit 1
fi

# Test 2: Cache stats
if curl -sf "$API_URL/metadata-cache/stats" > /dev/null; then
    echo "✓ Cache API OK"
else
    echo "✗ Cache API FAILED"
    exit 1
fi

# Test 3: Latência
LATENCY=$(curl -s -o /dev/null -w '%{time_total}' "$API_URL/")
if (( $(echo "$LATENCY < 1.0" | bc -l) )); then
    echo "✓ Latência OK (${LATENCY}s)"
else
    echo "⚠ Latência alta (${LATENCY}s)"
fi
```

---

## 5. Rastreamento de Requisições (Tracing)

### 5.1 correlation IDs
Para debug de problemas em produção, adicionar correlation ID em cada request:

```python
import uuid
from fastapi import Request

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    # Adicionar ao contexto de log
    logger.bind(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

### 5.2 Log de Requests
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": request.client.host
        }
    )
    return response
```

---

## 6. Ferramentas Recomendadas

| Ferramenta | License | Descrição |
|---|---|---|
| **Grafana OSS** | AGPL-3.0 | Dashboards e visualização |
| **Prometheus** | Apache-2.0 | Coleta de métricas |
| **Loki** | AGPL-3.0 | Agregação de logs |
| **Tempo** | AGPL-3.0 | Distributed tracing |
| **Uptime Kuma** | MIT | Health checks externos |
| **Promtail** | AGPL-3.0 | Coleta e envio de logs |

---

## 7. Implementação Atual

### 7.1 Já Implementado
- [x] Health check com verificação real de DB (`/health`)
- [x] Cache de metadados com estatísticas (`/metadata-cache/stats`)
- [x] Logs estruturados via `logging` module
- [x] Provenance de ingestões (`/provenance`)

### 7.2 Pendente
- [ ] Endpoint `/metrics` para Prometheus
- [ ] Middleware de correlation ID
- [ ] Dashboard Grafana de exemplo
- [ ] Alertas configurados
- [ ] Monitor externo (Uptime Kuma)

---

## 8. Referências

- Health check: `functions/main.py` → `GET /health`
- Cache stats: `functions/common/metadata_cache.py` → `GET /metadata-cache/stats`
- Logging: Python `logging` module
- Scripts de backup: `scripts/backup_postgres.sh`
- Scripts de teste: `scripts/test_restore.sh`