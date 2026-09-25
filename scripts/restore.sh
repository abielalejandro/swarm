#!/bin/bash

echo "🔄 Restaurando backup del Swarm..."
echo "========================================"

# Listar backups disponibles
echo ""
echo "📂 Backups disponibles:"
ls -la /backups/ 2>/dev/null | grep "^d" | awk '{print "  " $9}' || echo "  No hay backups disponibles"

echo ""
read -p "Ingresa el nombre del backup a restaurar: " BACKUP_NAME

BACKUP_PATH="/backups/$BACKUP_NAME"
if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup no encontrado: $BACKUP_PATH"
    exit 1
fi

echo ""
echo "⚠️  Esto SOBRESCRIBIRÁ los datos actuales"
read -p "¿Continuar? (escribe 'yes'): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Restauración cancelada."
    exit 0
fi

echo ""
echo "🔄 Restaurando..."

# Restaurar Redis
if [ -f "$BACKUP_PATH/redis.rdb" ]; then
    echo "  🗄️ Restaurando Redis..."
    docker cp $BACKUP_PATH/redis.rdb swarm_redis:/data/dump.rdb
    docker exec swarm_redis redis-cli CONFIG SET save ''
    docker exec swarm_redis redis-cli CONFIG SET appendonly no
    docker exec swarm_redis redis-cli FLUSHALL
    docker exec swarm_redis redis-cli --rdb /data/dump.rdb
    docker exec swarm_redis redis-cli CONFIG SET appendonly yes
    docker exec swarm_redis redis-cli CONFIG SET save '900 1 300 10 60 10000'
    echo "  ✅ Redis restaurado"
fi

# Restaurar Postgres
if [ -f "$BACKUP_PATH/postgres.sql" ]; then
    echo "  🐘 Restaurando Postgres..."
    docker exec -i swarm_postgres psql -U swarm -d swarm_audit < $BACKUP_PATH/postgres.sql
    echo "  ✅ Postgres restaurado"
fi

# Restaurar Qdrant
if [ -d "$BACKUP_PATH/qdrant" ]; then
    echo "  🔍 Restaurando Qdrant..."
    docker cp $BACKUP_PATH/qdrant/. swarm_qdrant:/qdrant/storage/
    echo "  ✅ Qdrant restaurado"
fi

echo ""
echo "✅ Restauración completada"
echo ""
echo "🔄 Reiniciando servicios..."
docker compose restart

echo ""
echo "✅ Servicios reiniciados"