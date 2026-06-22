# ADRs — Architectural Decision Records

Índice de decisões arquiteturais do projeto Poshboard (RPV).

## ADRs Implementados

| # | Título | Data | Status | Localização |
|---|---|---|---|---|
| 0001 | Firestore em vez de RTDB | 2026-06 | Implementado parcialmente | [docs/adr/0001-firestore-em-vez-de-rtdb.md](adr/0001-firestore-em-vez-de-rtdb.md) |
| 0002 | Manutenção sem reengenharia | 2026-06 | Implementado | [docs/adr/0002-manutencao-sem-reengenharia.md](adr/0002-manutencao-sem-reengenharia.md) |
| 0003 | Cloud Run em vez de Firebase Functions | 2026-06 | Implementado | [docs/adr/0003-cloud-run-em-vez-de-firebase-functions.md](adr/0003-cloud-run-em-vez-de-firebase-functions.md) |
| 0004 | Modelo Raw e Canonical | 2026-06 | Implementado | [docs/adr/0004-modelo-raw-e-canonical.md](adr/0004-modelo-raw-e-canonical.md) |
| 0005 | Handlers síncronos como dívida técnica | 2026-06 | Conhecido | [docs/adr/0005-handlers-sincronos-divida-tecnica.md](adr/0005-handlers-sincronos-divida-tecnica.md) |
| 0006 | Correção do drift de configuração (SSQM/CLS-07) | 2026-06-21 | Aceito parcialmente | [docs/ADR-001-config-drift.md](ADR-001-config-drift.md) |

## ADRs Propostos / Em Discussão

| # | Título | Issue Relacionada | Status |
|---|---|---|---|
| 0007 | Backups automatizados e plano de continuidade | #16 | ✅ Implementado |
| 0008 | Cache/mirror de metadados acadêmicos | #17 | ✅ Implementado |
| 0009 | Observabilidade independente de provedor | #18 | ✅ Implementado (documentação) |
| 0010 | Revisão semestral do SSQM | #20 | Pendente |

## Template para Novos ADRs

Para criar um novo ADR, use o template abaixo em `docs/adr/NNNN-titulo.md`:

```markdown
# ADR-NNNN — Título da Decisão

**Status**: Proposto | Aceito | Implementado | Deprecated | Superseded  
**Data**: YYYY-MM-DD  
**Decisores**: [nomes]  
**Referências**: [links para issues, discussões, docs]

## Contexto

Qual é o problema ou situação que motivou esta decisão?

## Decisão

O que foi decidido? Descreva a arquitetura, padrão, ou abordagem escolhida.

## Consequências

### Positivas
- O que melhora com esta decisão?
- Quais benefícios traz?

### Negativas
- Quais trade-offs foram aceitos?
- O que se perde ou complica?

### Neutras / Atendimentos
- O que precisa ser feito para implementar?
- Quais devem ser os próximos passos?

## Status

Detalhe o status atual e critérios para mudança.

## Referências

- Link para issue relacionado
- Link para discussão
- Outros documents relevantes
```

## Relacionado com SSQM

Os ADRs estão alinhados com as iniciativas do **SSQM (Sistema de Soberania e Qualidade de Manutenção)**:

| Smell SSQM | ADR Relacionado | Descrição |
|---|---|---|
| CLS-07 | ADR-001 | Configuration drift |
| CLS-06 | ADR-008 | Dependência de APIs externas |
| CLS-08 | Este índice | Documentação arquitetural desalinhada |

---

**Manutenção**: Este índice deve ser atualizado sempre que um novo ADR for criado.