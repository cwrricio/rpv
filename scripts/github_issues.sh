#!/usr/bin/env bash
# SSQM — cria as issues do roadmap no GitHub.
# Pré-requisito: gh autenticado (`gh auth login -h github.com`).
# Uso: bash scripts/github_issues.sh
set -euo pipefail

REPO="${REPO:-cwrricio/rpv}"

echo "Criando issues em $REPO ..."

mkissue() {
  local title="$1"; local body="$2"; local labels="$3"
  # cria labels se não existирem (ignora erro se já existem)
  IFS=',' read -ra LBL <<< "$labels"
  for l in "${LBL[@]}"; do
    gh label create "$l" --repo "$REPO" >/dev/null 2>&1 || true
  done
  gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels"
}

mkissue "SSQM F1 — Camada de portas/adaptadores de armazenamento" \
"Introduzir StoragePort e adaptadores (Firebase/Postgres) para que BaseCRUD não dependa do provedor.
- [x] StoragePort (functions/repositories/ports.py)
- [x] FirebaseRTDBAdapter
- [x] factory get_storage()
- [x] BaseCRUD delega ao StoragePort
- [x] remover firebase_admin.db de services/pesquisa.py e main.py
Smells: CLS-01, CLS-02. Implementado na branch SSQM." \
"ssqm,arquitetura"

mkissue "SSQM F2 — Frontend consome somente a API (remover RTDB)" \
"Remover fallbacks *.firebaseio.com/*.json e VITE_RTDB_URL das telas e a dep firebase do package.json.
- [x] Home.jsx, Home/Home.jsx, RelatorioProducao.jsx, Qualis.jsx
- [x] remover firebase de apresentacao/package.json
Smells: CLS-03, CLS-09. Implementado na branch SSQM." \
"ssqm,frontend"

mkissue "SSQM F3 — Exportação de dados, modelo canônico e drift de config" \
"- [x] scripts/export_rtdb.py (JSON/CSV versionado)
- [x] docs/DATA_MODEL.md
- [x] docs/ADR-001-config-drift.md (hosting dir corrigido)
Smell: CLS-07. Implementado na branch SSQM." \
"ssqm,governanca"

mkissue "SSQM F4 — Adaptador PostgreSQL + Docker em tudo" \
"- [x] PostgresAdapter (SQLAlchemy, kv_store)
- [x] STORAGE_BACKEND/DATABASE_URL em settings
- [x] Dockerfile.backend, apresentacao/Dockerfile, docker-compose.yml
- [x] testes TDD (SQLite)
Smell: CLS-01 (infra). Implementado na branch SSQM." \
"ssqm,infra"

mkissue "SSQM — Portar queries RTDB para o StoragePort (dívida)" \
"Eliminar o escape hatch BaseCRUD.ref()/raw_ref():
- [ ] DocenteCRUD.find_by_orcid (order_by_child orcid)
- [ ] PesquisaService.listar (order_by_child status)
Ver docs/DATA_MODEL.md." \
"ssqm,arquitetura"

mkissue "SSQM — Migração de dados RTDB -> PostgreSQL" \
"Script de migração com validação e rollback (médio prazo do roadmap), usando export JSON como fonte." \
"ssqm,dados"

mkissue "SSQM — Definir project id Firebase único (governança)" \
"Unificar 'poshbard' (.firebaserc/RTDB) e 'metaorganizer-project' (workflows). Decisão humana pendente — ver ADR-001." \
"ssqm,governanca"

echo "Concluído."
