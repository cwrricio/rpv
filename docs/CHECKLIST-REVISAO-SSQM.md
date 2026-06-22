# CHECKLIST DE REVISÃO SEMESTRAL SSQM

**Propósito**: Tornar a soberania uma prática contínua, reavaliando o SSQMScore/IDAN e atualizando inventário de dependências a cada semestre.

**Frequência**: Semestral (junho e dezembro)  
**Responsável**: Tech Lead + 1 membro da equipe  
**Duração Estimada**: 16-32 horas

---

## Pré-Requisitos

- [ ] Acessar repositório GitHub
- [ ] Acessar documentação em `docs/`
- [ ] Ter acesso ao dashboard de métricas (se disponível)
- [ ] Checklist versionado no `docs/CHECKLIST-REVISAO-SSQM.md`

---

## 1. Atualizar Inventário de Dependências (DEP-xx)

### 1.1 Dependências de Infraestrutura

| ID | Dependência | Tipo | Crítica? | Mitigação | Status |
|---|---|---|---|---|---|
| DEP-001 | PostgreSQL | Banco de dados | Sim | Backups diários, restore testado semanal | ✓ Ativo |
| DEP-002 | OpenAlex API | API externa | Não | Cache local (7-30 dias) | ✓ Mitigado |
| DEP-003 | ORCID API | API externa | Não | Cache local (7 dias) | ✓ Mitigado |
| DEP-004 | Crossref API | API externa | Não | Cache local (30 dias) | ✓ Mitigado |
| DEP-005 | Semantic Scholar API | API externa | Não | Cache local (30 dias) | ✓ Mitigado |
| DEP-006 | Firebase RTDB | Banco (legado) | Não | StoragePort permite troca para Postgres | ✓ Portabilidade |

**Ações**:
- [ ] Verificar se novas dependências foram adicionadas
- [ ] Atualizar status das mitigações
- [ ] Identificar novas dependências críticas sem mitigação

### 1.2 Dependências de Código (Python)

```bash
# Gerar lista atualizada
pip list --format=freeze > requirements-current.txt
# Comparar com requirements.txt
diff requirements.txt requirements-current.txt
```

- [ ] Atualizar `requirements.txt` com versões estáveis mais recentes
- [ ] Identificar dependências descontinuadas ou com vulnerabilidades
- [ ] Verificar se todas as dependências têm versão pinada

### 1.3 Dependências de Código (Node.js)

```bash
# Gerar lista atualizada
cd apresentacao && npm list --depth=0
```

- [ ] Atualizar `package.json` com versões estáveis
- [ ] Verificar vulnerabilidades com `npm audit`
- [ ] Remover dependências não utilizadas

---

## 2. Reavaliar Smells CLS-xx

### 2.1 Smells Conhecidos

| ID | Smell | severidade | Status | Notas |
|---|---|---|---|---|
| CLS-06 | Dependência de APIs externas | Médio | ✓ Mitigado | Cache implementado (Issue #17) |
| CLS-07 | Configuration drift | Baixo | ✓ Resolvido | ADR-001, Docker em tudo |
| CLS-08 | Documentação desalinhada | Baixo | ✓ Resolvido | ARCHITECTURE.md + ADR-INDEX |

### 2.2 Novos Smells Identificados

Durante a revisão, identificar novos smells usando critérios:

- **Acoplamento excessivo**: Módulo que conhece muitos outros
- **Configuração hardcoded**: Values que deveriam ser env vars
- **Fallback ausente**: Dependência externa sem cache/alternativa
- **Documentação divergente**: Docs vs código implementado
- **Testes frágeis**: Tests que breakam com mudanças internas

**Novos smells encontrados**:
```
[Escrever aqui]
```

---

## 3. Calcular SSQMScore (Baseline: 43.3%, Nível 3)

### 3.1 Dimensões Avaliadas

| Dimensão | Peso | Score (0-100) | Justificativa |
|---|---|---|---|
| **Soberania de Dados** | 25% | 80 | Backups automatizados, restore testado, PostgreSQL portável |
| **Portabilidade** | 20% | 90 | StoragePort, Docker, zero vendor lock-in operacional |
| **Observabilidade** | 15% | 60 | Health checks OK, logs estruturados, falta dashboards |
| **Resiliência** | 20% | 75 | Cache de APIs, retry, falta circuit breaker |
| **Documentação** | 10% | 85 | ADRs, ARCHITECTURE.md, ISSUES-IMPLEMENTADAS |
| **Governança** | 10% | 50 | Revisão semestral implementada, falta histórico |

**Cálculo**:
```
SSQMScore = Σ (Peso × Score) / 100
          = (25×80 + 20×90 + 15×60 + 20×75 + 10×85 + 10×50) / 100
          = (2000 + 1800 + 900 + 1500 + 850 + 500) / 100
          = 7550 / 100
          = 75.5%
```

**Evolução**:
- **Baseline (2026-06)**: 43.3% (Nível 3)
- **Revisão 1 (2026-12)**: [A calcular]
- **Revisão 2 (2027-06)**: [A calcular]

### 3.2 Níveis de Maturidade

| Nível | Score Range | Características |
|---|---|---|
| 1 | 0-30% | Dependência total de vendor, sem backups,_docs incompletos |
| 2 | 31-50% | Backups manuais, alguma documentação, vendor lock-in parcial |
| 3 | 51-70% | Backups automatizados, portabilidade, observabilidade básica |
| 4 | 71-90% | Resiliência ativa, dashboards, governance contínua |
| 5 | 91-100% | Soberania total, multi-cloud, auto-cura, governança madura |

**Status atual**: Nível 3 → 4 (em progresso)

---

## 4. Revisar Processos de Backup e DR

### 4.1 Métricas de Backup

| Métrica | Meta | Atual | Status |
|---|---|---|---|
| Frequência de backup | Diário | Diário (cron) | ✓ |
| Retenção | 30 dias | 30 dias | ✓ |
| Teste de restore | Semanal | Semanal (cron) | ✓ |
| RTO (Recovery Time Objective) | < 4 horas | [medir] | ⚠ |
| RPO (Recovery Point Objective) | < 24 horas | 24 horas | ✓ |

### 4.2 Drills de DR

- [ ] Simular falha de banco e executar restore
- [ ] Medir tempo real de recuperação
- [ ] Documentar lições aprendidas

---

## 5. Atualizar Roadmap SSQM

### 5.1 Iniciativas Completadas (Último Semestre)

- [x] #16 — Backups automatizados, restore testado e plano de continuidade
- [x] #17 — Cache/mirror local dos metadados acadêmicos essenciais
- [x] #18 — Observabilidade independente de provedor
- [x] #19 — Alinhar documentação arquitetural e ADRs
- [x] #20 — Revisão semestral do SSQM (esta issue)

### 5.2 Iniciativas Propostas (Próximo Semestre)

Sugestões:
- [ ] #21 — Dashboards Grafana para observabilidade
- [ ] #22 — Circuit breaker para APIs externas
- [ ] #23 — Multi-region failover (PostgreSQL read replica)
- [ ] #24 — Auditoria de segurança e hardening
- [ ] #25 — Documentação de APIs (OpenAPI/Swagger)

**Priorização**:
```
[Definir prioridades com base em impacto × esforço]
```

---

## 6. Lições Aprendidas

### 6.1 O que funcionou bem

- [Preencher]

### 6.2 O que pode melhorar

- [Preencher]

### 6.3 Ações para o próximo semestre

| Ação | Responsável | Prazo | Status |
|---|---|---|---|
| [Ex: Implementar dashboards] | [Nome] | [Data] | [ ] |

---

## 7. Aprovação e Próximos Passos

**Revisão realizada em**: [Data]  
**Participantes**: [Nomes]  
**SSQMScore calculado**: [XX.X%]  
**Nível de maturidade**: [1-5]

**Próxima revisão**: [Data + 6 meses]

**Assinaturas**:

- Tech Lead: ________________________ Data: __/__/____
- Equipe: ________________________ Data: __/__/____

---

## Anexo A — Histórico de Revisões

| Data | SSQMScore | Nível | Participantes | Notas |
|---|---|---|---|---|
| 2026-06-22 | 43.3% (baseline) | 3 | [Iniciais] | Implementação inicial SSQM |
| [Data] | [Score] | [Nível] | [Nomes] | [Notas] |

## Anexo B — Referências

- [docs/PLANO-CONTINUIDADE.md](PLANO-CONTINUIDADE.md)
- [docs/OBSERVABILIDADE.md](OBSERVABILIDADE.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/ADR-INDEX.md](ADR-INDEX.md)
- [docs/ISSUES-IMPLEMENTADAS.md](ISSUES-IMPLEMENTADAS.md)