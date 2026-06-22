# ADR-001 — Correção do drift de configuração (SSQM / CLS-07)

**Status:** Aceito — 2026-06-22
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
3. **Project id:** `poshbard` passa a ser o project id Firebase legado canonico.
   A decisao privilegia a fonte de dados ainda existente (`.firebaserc` e RTDB URL)
   e evita que os workflows legados publiquem em um projeto diferente do usado
   pelos scripts Firebase. Os workflows de Hosting deixam de apontar para
   `metaorganizer-project` e usam `FIREBASE_PROJECT_ID=poshbard`.

## Configuracao operacional

- `.firebaserc`: `projects.default = poshbard`.
- Workflows legados de Firebase Hosting: `FIREBASE_PROJECT_ID=poshbard`.
- Segredo esperado no GitHub: `FIREBASE_SERVICE_ACCOUNT_POSHBARD` ou, de forma
  generica, `FIREBASE_SERVICE_ACCOUNT`.
- `scripts/seed_rtdb.py`: usa `PROJECT_ID`, depois `FIREBASE_PROJECT_ID`, e por
  ultimo `poshbard`; a `RTDB_URL` padrao e derivada desse id.

## Consequências

- Build/hosting local reproduzível e coerente com a documentação.
- Migração para Docker/Postgres reduz a relevância do project id Firebase ao longo do tempo.
- O segredo antigo `FIREBASE_SERVICE_ACCOUNT_METAORGANIZER_PROJECT` fica obsoleto.
  Se o Hosting legado ainda for usado, ele precisa ser recriado/renomeado para o
  projeto `poshbard`.
