# PLANO DE CONTINUIDADE DE NEGÓCIOS E RECUPERAÇÃO DE DESASTRES

## Visão Geral
Este documento descreve os procedimentos para garantir a continuidade das operações e recuperação de desastres do sistema Poshboard (RPV).

---

## 1. Estratégia de Backup

### 1.1 Backups Automatizados
- **Frequência**: Diária (recomendado: 2h da manhã, horário de menor uso)
- **Retenção**: 30 dias
- **Localização**: Diretório `/backups` no servidor de produção
- **Formato**: PostgreSQL dump comprimido (gzip)
- **Validação**: Automática após cada backup (verifica tamanho > 0)

### 1.2 Configuração do Cron Job (Produção)
```bash
# Adicionar ao crontab (crontab -e)
0 2 * * * cd /path/to/rpv && ./scripts/backup_postgres.sh >> /var/log/rpv_backup.log 2>&1
```

### 1.3 Testes de Restore
- **Frequência**: Semanal (recomendado: domingo às 3h)
- **Procedimento**: Script `test_restore.sh` restaura em banco isolado e verifica integridade
- **Relatório**: Logs salvos em `/var/log/rpv_restore_test.log`

```bash
# Cron para teste semanal
0 3 * * 0 cd /path/to/rpv && ./scripts/test_restore.sh >> /var/log/rpv_restore_test.log 2>&1
```

---

## 2. Procedimentos de Recuperação

### 2.1 Recuperação de Dados (RTO: 4 horas, RPO: 24 horas)

#### Cenário: Corrupção de dados ou exclusão acidental
1. Identificar o backup mais recente antes do incidente
2. Notificar stakeholders sobre downttime estimado
3. Executar restore:
   ```bash
   cd /path/to/rpv
   ./scripts/restore_postgres.sh ./backups/backup_YYYYMMDD_HHMMSS.sql.gz --force
   ```
4. Validar integridade dos dados restaurados
5. Reiniciar serviços
6. Comunicar retomada das operações

#### Cenário: Falha de hardware do servidor de banco de dados
1. Provisionar novo servidor com PostgreSQL 16
2. Instalar dependencies do projeto
3. Copiar backups do servidor antigo (ou do storage externo)
4. Executar restore no novo servidor
5. Atualizar DNS/load balancer para apontar para novo servidor
6. Validar health checks

### 2.2 Recuperação de Desastre Completo

#### Dependências Identificadas
| Componente | Tipo | Crítico | Tempo de Recuperação |
|---|---|---|---|
| PostgreSQL | Banco de dados | Sim | 4 horas |
| Backend (FastAPI) | API | Sim | 1 hora |
| Frontend (React) | UI | Não | 2 horas |
| OpenAlex API | Externo | Não | N/A (fallback para cache) |
| ORCID API | Externo | Não | N/A (fallback para cache) |

#### Procedimento de DR Completo
1. **Prioridade 1**: Banco de dados (PostgreSQL)
   - Restaurar do último backup válido
   - Tempo estimado: 30-60 minutos (depende do tamanho)

2. **Prioridade 2**: Backend
   - Deploy via Docker Compose ou Kubernetes
   - Configurar variáveis de ambiente
   - Validar health check: `GET /health`

3. **Prioridade 3**: Frontend
   - Build e deploy da aplicação React
   - Validar conexão com API

4. **Prioridade 4**: Serviços de ingestão
   - Reiniciar workers de coleta de dados
   - Validar APIs externas (OpenAlex, ORCID)

---

## 3. Health Checks e Monitoramento

### 3.1 Endpoints de Health Check
- ** `/health`**: Status do backend e banco de dados
  - Retorna HTTP 200 se saudável
  - Retorna HTTP 503 se banco indisponível
  - Incluído no `docker-compose.yml` como healthcheck

### 3.2 Monitoramento Recomendado
```yaml
# docker-compose.yml (adicionar)
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 3.3 Alertas
Configurar alertas para:
- Backup falhar (exit code != 0)
- Health check retornar 503
- Teste de restore semanal falhar
- Disco com menos de 20% livre (backups)

---

## 4. Matriz de Responsabilidades

| Atividade | Responsável | Frequência |
|---|---|---|
| Monitorar backups diários | Scripts automáticos | Diário |
| Revisar logs de backup | Equipe de infra | Semanal |
| Teste de restore | Scripts automáticos | Semanal |
| Revisão do plano de DR | Tech lead | Semestral |
| Atualizar documentação | Equipe | Conforme mudanças |

---

## 5. Contatos de Emergência

| Papel | Contato | Telefone |
|---|---|---|
| On-call Infra | [definir] | [definir] |
| Tech Lead | [definir] | [definir] |
| Product Owner | [definir] | [definir] |

---

## 6. Histórico de Testes de DR

| Data | Tipo | Resultado | Tempo de Recuperação | Observações |
|---|---|---|---|---|
| [Primeiro teste] | Restore completo | [ ] Aprovado [ ] Reprovado | X minutos | [notas] |

---

## 7. Referências

- Scripts de backup: `scripts/backup_postgres.sh`
- Scripts de restore: `scripts/restore_postgres.sh`
- Scripts de teste: `scripts/test_restore.sh`
- Health check endpoint: `functions/main.py` → `GET /health`
- Configuração Docker: `docker-compose.yml`