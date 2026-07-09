#!/bin/bash
# Script de backup automatizado do PostgreSQL
# Uso: ./scripts/backup_postgres.sh [backup_dir]
#
# Cria um dump versionado do banco PostgreSQL com:
# - Timestamp no nome do arquivo
# - Compressão gzip
# - Validação do backup (verifica se arquivo foi criado e tem tamanho > 0)
# - Cleanup de backups antigos (maintém últimos N backups)
#
# Variáveis de ambiente:
#   BACKUP_DIR: diretório para salvar backups (padrão: ./backups)
#   DATABASE_URL: conexão PostgreSQL (padrão: do .env ou docker-compose)
#   BACKUP_RETENTION_DAYS: quantos dias manter backups (padrão: 30)

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Extrair dados de conexão do DATABASE_URL
# Formato: postgresql+psycopg://user:pass@host:port/dbname
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\):.*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
export PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

# Se estiver dentro do container Docker, usa host direto
if [ -n "$DB_HOST" ] && [ "$DB_HOST" = "db" ]; then
    DB_HOST="localhost"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "=== Backup PostgreSQL ==="
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Backup file: $BACKUP_FILE"
echo ""

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

# Executar pg_dump com compressão
# Usa pg_dump do host (precisa ter postgres-client instalado) ou roda via docker
if command -v pg_dump &> /dev/null; then
    echo "Usando pg_dump local..."
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"
else
    echo "pg_dump não encontrado, usando Docker..."
    docker exec rpv-db-1 pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"
fi

# Verificar se backup foi criado com sucesso
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo ""
    echo "✓ Backup criado com sucesso: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "✗ ERRO: Backup falhou ou arquivo está vazio"
    exit 1
fi

# Cleanup de backups antigos
echo ""
echo "=== Cleanup de backups antigos (> $BACKUP_RETENTION_DAYS dias) ==="
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +$BACKUP_RETENTION_DAYS -exec rm -v {} \;

# Listar backups existentes
echo ""
echo "=== Backups disponíveis ==="
ls -lht "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null || echo "Nenhum backup encontrado"

echo ""
echo "=== Backup completado ==="