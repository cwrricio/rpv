#!/usr/bin/env bash
# SSQM — Parte 2: issues do roadmap (medio/longo prazo) ainda nao criadas.
# Cobre smells CLS-04, CLS-05, CLS-06, CLS-08 e itens de governanca/observabilidade.
# Pre-requisito: gh autenticado (`gh auth login -h github.com`).
# Uso: bash scripts/github_issues_parte2.sh
set -euo pipefail

REPO="${REPO:-cwrricio/rpv}"

echo "Criando issues (parte 2) em $REPO ..."

mkissue() {
  local title="$1"; local body="$2"; local labels="$3"
  IFS=',' read -ra LBL <<< "$labels"
  for l in "${LBL[@]}"; do
    gh label create "$l" --repo "$REPO" >/dev/null 2>&1 || true
  done
  gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels"
}

# ---------- Curto prazo restante ----------

mkissue "SSQM — Camada de clientes externos com cache, timeout e retry (CLS-06)" \
"Encapsular OpenAlex/ORCID/Crossref/Semantic Scholar atras de uma camada de cliente unica com timeout padrao, retries com backoff, rate limiting e cache local. A coleta de dados em si NAO muda (requisito), apenas ganha robustez.
- [ ] Cliente HTTP comum (timeout + retry/backoff + rate limit)
- [ ] Cache local de respostas (snapshots reutilizaveis)
- [ ] Tratamento de quota/indisponibilidade por fornecedor
- [ ] Testes de timeout/retry (TDD)
Smell: CLS-06 (External API Lock-In). Roadmap curto prazo (32-64 h)." \
"ssqm,ingestao"

mkissue "SSQM — Cobertura de testes para repositorios e endpoints principais" \
"Ampliar a suite de testes alem dos adaptadores ja cobertos, reduzindo o risco da troca de banco.
- [ ] Testes de contrato do StoragePort para todos os CRUDs
- [ ] Testes dos endpoints FastAPI principais
- [ ] Testes de borda do FirebaseRTDBAdapter (com emulador opt-in)
Roadmap curto prazo (40-80 h)." \
"ssqm,testes"

mkissue "SSQM — Credenciais independentes do Google ADC (CLS-04)" \
"Remover a exigencia de GOOGLE_APPLICATION_CREDENTIALS/ADC para operar a aplicacao.
- [ ] Secrets/config independentes do provedor para o backend
- [ ] App sobe sem credenciais Google quando STORAGE_BACKEND=postgres (validar e documentar)
- [ ] Atualizar README removendo passos ADC obrigatorios
Smell: CLS-04 (Identity/Operational Lock-In)." \
"ssqm,governanca"

# ---------- Medio prazo ----------

mkissue "SSQM — Separar ingestao pesada em jobs/worker com fila e retries (CLS-06)" \
"Mover a ingestao academica de rotas HTTP sincronas para jobs/worker com fila, retries e idempotencia.
- [ ] Definir mecanismo de fila (ex.: RQ/Celery/Arq) sem lock-in proprietario
- [ ] Worker dedicado no docker-compose
- [ ] Retries, dead-letter e observabilidade basica dos jobs
Smell: CLS-06. Roadmap medio prazo (80-160 h)." \
"ssqm,ingestao,infra"

mkissue "SSQM — Pipeline CI/CD portavel documentado (CLS-05)" \
"Documentar e tornar o pipeline executavel em GitHub Actions, GitLab CI ou Jenkins, sem acoplar a FirebaseExtended/action-hosting-deploy.
- [ ] Pipeline de build/test/deploy baseado nas imagens Docker
- [ ] Remover passos especificos de Firebase Hosting
- [ ] Documentar variaveis/secrets necessarias por plataforma
Smell: CLS-05 (Infrastructure/DevOps Lock-In). Roadmap medio prazo (24-48 h)." \
"ssqm,infra,cicd"

mkissue "SSQM — Estrategia de autenticacao propria (opcional, DEP-03)" \
"Caso login real seja necessario, definir autenticacao independente do provedor (ex.: Keycloak/OIDC self-hosted) em vez de identidade Google.
- [ ] Levantar requisitos de autenticacao reais do produto
- [ ] ADR comparando opcoes self-hosted vs gerenciadas
- [ ] Prova de conceito se aprovado
Roadmap medio prazo (40-120 h). Depende de decisao de produto." \
"ssqm,governanca,seguranca"

# ---------- Longo prazo ----------

mkissue "SSQM — Operar versao sem Firebase em ambiente proprio/hibrido (CLS-05)" \
"Meta de soberania: rodar o sistema completo (STORAGE_BACKEND=postgres) em VPS/Kubernetes/Cloud Run sem nenhuma dependencia Firebase em runtime.
- [ ] Validar app end-to-end sem credenciais/servicos Firebase
- [ ] Deploy reproduzivel documentado para ambiente proprio
- [ ] Plano de corte/coexistencia durante a transicao
Smell: CLS-01..CLS-05. Roadmap longo prazo (160-320 h)." \
"ssqm,infra"

mkissue "SSQM — Backups automatizados, restore testado e plano de continuidade" \
"Garantir soberania e recuperabilidade dos dados no PostgreSQL.
- [ ] Backup automatizado (dump versionado/agendado)
- [ ] Restore testado periodicamente (nao apenas backup)
- [ ] Plano de continuidade documentado e health checks externos
Roadmap longo prazo (80-160 h)." \
"ssqm,dados,infra"

mkissue "SSQM — Cache/mirror local dos metadados academicos essenciais (CLS-06)" \
"Manter espelho/cache local (snapshots OpenAlex etc.) para reduzir dependencia de disponibilidade/quota das APIs externas.
- [ ] Definir conjunto minimo de metadados a espelhar
- [ ] Estrategia de atualizacao incremental
- [ ] Fallback automatico para cache quando API externa falhar
Smell: CLS-06. Roadmap longo prazo (80-200 h)." \
"ssqm,ingestao,dados"

mkissue "SSQM — Observabilidade independente de provedor" \
"Implantar logs, metricas e health checks proprios (ex.: Prometheus/Grafana/Loki self-hosted), nao evidenciados hoje.
- [ ] Logs estruturados no backend e worker
- [ ] Metricas e health checks expostos
- [ ] Dashboards e alertas independentes do Google
Roadmap longo prazo (40-120 h)." \
"ssqm,observabilidade,infra"

# ---------- Governanca/Conhecimento ----------

mkissue "SSQM — Alinhar documentacao arquitetural e ADRs (CLS-08)" \
"O documento interno cita ADRs e docs/ARCHITECTURE.md que nao existem no inventario. Consolidar a documentacao arquitetural com a arquitetura de portas/adaptadores ja implementada.
- [ ] Criar/atualizar docs/ARCHITECTURE.md (portas/adaptadores, Docker)
- [ ] Indexar ADRs existentes (ADR-001) e pendentes
- [ ] Remover referencias divergentes
Smell: CLS-08 (Knowledge/Strategic Smell)." \
"ssqm,governanca,docs"

mkissue "SSQM — Revisao semestral do SSQM e inventario de dependencias" \
"Tornar a soberania uma pratica continua: reavaliar o SSQMScore/IDAN e atualizar o inventario de dependencias a cada semestre.
- [ ] Checklist de revisao SSQM versionado
- [ ] Atualizar inventario DEP-xx e smells CLS-xx
- [ ] Registrar evolucao do SSQMScore (baseline 43,3%, Nivel 3)
Roadmap longo prazo / governanca continua (16-32 h por ciclo)." \
"ssqm,governanca"

echo "Concluido."
