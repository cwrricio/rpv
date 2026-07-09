#!/bin/bash
# Script de restore do PostgreSQL
# Uso: ./scripts/restore_postgres.sh <backup_file> [--dry-run]
#
# Restaura um backup versionado do PostgreSQL com:
# - Validação do arquivo de backup
# - Confirmação antes de destruir dados (a menos que --force)
# - Teste de integridade do backup antes do restore
# - Log de todas as operações
#
# Variáveis de ambiente:
#   DATABASE_URL: conexão PostgreSQL (padrão: do .env ou docker-compose)

set -e

DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard}"
DRY_RUN=false
FORCE=false
BACKUP_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            if [ -z "$BACKUP_FILE" ]; then
                BACKUP_FILE="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <backup_file> [--dry-run] [--force]"
    echo ""
    echo "Opções:"
    echo "  --dry-run  Valida o backup sem restaurar"
    echo "  --force    Restaura sem pedir confirmação"
    echo ""
    echo "Backups disponíveis:"
    ls -lht ./backups/backup_*.sql.gz 2>/dev/null | head -10 || echo "  Nenhum backup encontrado em ./backups/"
    exit 1
fi

# Validar arquivo de backup
if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ ERRO: Arquivo de backup não encontrado: $BACKUP_FILE"
    exit 1
fi

echo "=== Validação do Backup ==="
echo "Arquivo: $BACKUP_FILE"
BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
echo "Tamanho: $BACKUP_SIZE"

# Verificar se o arquivo é um gzip válido
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "✗ ERRO: Arquivo não é um gzip válido ou está corrompido"
    exit 1
fi
echo "✓ Arquivo gzip válido"

# Extrair dados de conexão do DATABASE_URL
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\):.*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
export PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

if [ "$DB_HOST" = "db" ]; then
    DB_HOST="localhost"
fi

echo ""
echo "=== Dados de Conexão ==="
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "=== DRY RUN ==="
    echo "Apenas validando backup, sem restaurar..."
    
    # Testar descompressão e ler primeiras linhas
    echo ""
    echo "=== Primeiras linhas do SQL ==="
    zcat "$BACKUP_FILE" | head -20
    
    echo ""
    echo "=== Contagem de comandos SQL ==="
    zcat "$BACKUP_FILE" | grep -c "^[^-]" || echo "0 linhas de SQL"
    
    echo ""
    echo "✓ Validação completada com sucesso"
    exit 0
fi

# Pedir confirmação (a menos que --force)
if [ "$FORCE" != true ]; then
    echo ""
    echo "⚠️  ATENÇÃO: Este restore vai DESTRUIR todos os dados atuais no banco '$DB_NAME'"
    echo ""
    read -p "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): " CONFIRM
    if [ "$CONFIRM" != "SIM" ]; then
        echo "Restore cancelado"
        exit 0
    fi
fi

echo ""
echo "=== Iniciando Restore ==="

# Criar dump de segurança do estado atual (caso algo dê errado)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFETY_BACKUP="./backups/safety_backup_before_restore_${TIMESTAMP}.sql.gz"
echo "Criando backup de segurança do estado atual: $SAFETY_BACKUP"
mkdir -p ./backups

if command -v pg_dump &> /dev/null; then
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null | gzip > "$SAFETY_BACKUP" || echo "  (backup de segurança falhou, continuando...)"
else
    docker exec rpv-db-1 pg_dump -U "$DB_USER" -d "$DB_NAME" 2>/dev/null | gzip > "$SAFETY_BACKUP" || echo "  (backup de segurança falhou, continuando...)"
fi

# Dropar e recriar o banco
echo ""
echo "Dropando banco existente..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" 2>/dev/null || true

echo "Criando banco novo..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"

echo ""
echo "Restaurando dados do backup..."
zcat "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"

echo ""
echo "=== Verificação Pós-Restore ==="

# Contar registros (assumindo que existem tabelas padrão do projeto)
echo "Verificando tabelas restauradas..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" || echo "  (nenhuma tabela encontrada ou erro na consulta)"

echo ""
echo "✓ Restore completado com sucesso!"
echo ""
echo "Backup de segurança criado em: $SAFETY_BACKUP"