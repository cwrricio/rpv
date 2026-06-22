# Script de teste automatizado de restore
# Uso: ./scripts/test_restore.sh
#
# Este script testa periodicamente que os backups estão funzionais:
# 1. Pega o backup mais recente
# 2. Cria um banco de teste isolado
# 3. Restaura o backup nele
# 4. Verifica integridade dos dados
# 5. Dropa o banco de teste
#
# Pode ser agendado via cron para rodar semanalmente

set -e

DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TEST_DB_NAME="poshboard_test_restore"

echo "=== Teste Automatizado de Restore ==="
echo "Data: $(date)"
echo ""

# Extrair dados de conexão
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\):.*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
export PGPASSWORD=*** "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

if [ "$DB_HOST" = "db" ]; then
    DB_HOST="localhost"
fi

# Encontrar backup mais recente
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "✗ ERRO: Nenhum backup encontrado em $BACKUP_DIR"
    exit 1
fi

echo "Backup mais recente: $LATEST_BACKUP"
echo ""

# Validar integridade do backup
echo "=== Validação ==="
if ! gzip -t "$LATEST_BACKUP"; then
    echo "✗ ERRO: Backup corrompido"
    exit 1
fi
echo "✓ Backup íntegro"

# Criar banco de teste
echo ""
echo "=== Criando banco de teste '$TEST_DB_NAME' ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${TEST_DB_NAME};" 2>/dev/null || true
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${TEST_DB_NAME};"

# Restaurar backup no banco de teste
echo ""
echo "=== Restaurando backup ==="
zcat "$LATEST_BACKUP" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME"

# Verificar integridade
echo ""
echo "=== Verificando integridade ==="
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "Tabelas restauradas: $TABLE_COUNT"

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✓ Banco restaurado com $TABLE_COUNT tabelas"
else
    echo "⚠ Nenhuma tabela encontrada (pode ser esperado se banco estava vazio)"
fi

# Cleanup
echo ""
echo "=== Cleanup ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${TEST_DB_NAME};"
echo "Banco de teste removido"

echo ""
echo "✓ Teste de restore completado com sucesso"