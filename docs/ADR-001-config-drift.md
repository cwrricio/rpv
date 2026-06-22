# ADR-001 — Correção do drift de configuração (SSQM / CLS-07)

**Status:** Aceito (parcial) — 2026-06-21
**Contexto SSQM:** smell CLS-07 (Governance/Configuration) do relatório SSQM.

## Problema

Configurações de ambiente/projeto divergiam entre arquivos:

| Item | Antes | Observação |
|---|---|---|
| Diretório de hosting | `firebase.json` → `public` | README descreve `apresentacao/dist` (saída real do Vite). |
| Project id (data) | `.firebaserc` → `poshbard` | Código usava ora `poshbard`, ora `poshboard` (typo). |
| Project id (deploy) | workflows → `metaorganizer-project` | Diverge do `.firebaserc`. |

## Decisão

1. **Hosting dir:** `firebase.json` passa a apontar para `apresentacao/dist`,
   alinhado ao README e à saída real do build. ✅ aplicado.
2. **Estratégia de deploy:** com a diretriz "Docker em tudo", o caminho canônico
   de publicação passa a ser containers (`docker-compose.yml`, `Dockerfile.backend`,
   `apresentacao/Dockerfile`). O Firebase Hosting fica como **legado em depreciação**.
3. **Project id:** os nomes `poshbard` (`.firebaserc`/RTDB) e `metaorganizer-project`
   (workflows) **precisam ser unificados pela equipe** — exige saber qual é o projeto
   Firebase/GCP realmente ativo. Não foi alterado automaticamente para não quebrar o
   deploy real. **Ação pendente** (ver issue de governança).

## Consequências

- Build/hosting local reproduzível e coerente com a documentação.
- Migração para Docker/Postgres reduz a relevância do project id Firebase ao longo do tempo.
- Resta uma decisão humana sobre o project id único, rastreada como issue.
