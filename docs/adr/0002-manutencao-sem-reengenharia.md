# ADR 0002 — Manutenção e evolução sem reengenharia arquitetural

**Status:** Decidido  
**Data:** 2026-05-11

## Contexto

O projeto foi desenvolvido durante uma disciplina de graduação e apresenta problemas de qualidade de código. Na disciplina de manutenção e evolução, surgiu a questão: refazer a arquitetura do zero (reengenharia) ou melhorar o que existe?

O `ARCHITECTURE.md` já documenta uma proposta de arquitetura em camadas (hexagonal/clean). O código atual viola essa proposta em vários pontos, mas a estrutura geral (`functions/` + FastAPI + Firebase) já existe e funciona.

As alternativas consideradas foram:

1. **Reengenharia completa** — redesenhar pastas, renomear tudo para hexagonal puro, reescrever camadas do zero.
2. **Manutenção dirigida** — corrigir bugs, eliminar duplicações, mover lógica para os lugares certos dentro da estrutura existente, renomear o que está claramente errado (ex.: `crud/` → `repositories/`).

## Decisão

**Manutenção dirigida, sem reengenharia.**

## Justificativa

- O projeto está em disciplina de *manutenção e evolução*, não de redesign.
- A estrutura `functions/` + FastAPI + Firebase é funcional e implantável — não há razão técnica para descartá-la.
- Reengenharia tem alto risco de introduzir regressões sem benefício proporcional em um projeto deste porte.
- Os problemas prioritários (bugs, duplicação de código, lógica fora do lugar) podem ser resolvidos dentro da estrutura atual.

## O que muda (manutenção permitida)

- Renomear `crud/` → `repositories/` — o nome atual não reflete o papel da pasta.
- Corrigir typo `commom/` → `common/`.
- Centralizar acesso ao banco em `repositories/`, eliminando as definições de `_db()` espalhadas por 5+ arquivos.
- Mover lógica de negócio inline em `main.py` para `services/`.
- Corrigir o bug `self._node()` → `self.ref()` em `docente_crud.py`.
- Usar o enum `TipoDocente` de `domain/types.py` onde está duplicado.

## O que não muda

- Estrutura geral de pastas dentro de `functions/`.
- FastAPI como framework HTTP.
- Firebase Auth e Firebase Hosting.
- O modelo de jobs agendados via Cloud Scheduler + Cloud Run.

## Consequências

- O código evolui de forma incremental, com histórico de git legível.
- A migração futura para Firestore (ADR 0001) é viabilizada pela centralização em `repositories/` — essa é a única mudança estrutural que precisa acontecer antes da migração de banco.
