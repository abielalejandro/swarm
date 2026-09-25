#!/bin/bash

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "📦 Haciendo backup del Swarm..."
echo "========================================"

# Backup Redis
echo ""
echo "🗄️ Backup Redis..."
if docker exec swarm_redis redis-cli SAVE > /dev/null 2>&1; then
    docker cp swarm_redis:/data/dump.rdb $BACKUP_DIR/redis.rdb 2>/dev/null
    echo -e "  ✅ Redis backup: $BACKUP_DIR/redis.rdb"
else
    echo -e "  ❌ Error en backup de Redis"
fi

# Backup Qdrant
echo ""
echo "🔍 Backup Qdrant..."
if docker cp swarm_qdrant:/qdrant/storage $BACKUP_DIR/qdrant/ 2>/dev/null; then
    echo -e "  ✅ Qdrant backup: $BACKUP_DIR/qdrant/"
else
    echo -e "  ❌ Error en backup de Qdrant"
fi

# Backup Postgres
echo ""
echo "🐘 Backup Postgres..."
if docker exec swarm_postgres pg_dump -U swarm swarm_audit > $BACKUP_DIR/postgres.sql 2>/dev/null; then
    echo -e "  ✅ Postgres backup: $BACKUP_DIR/postgres.sql"
else
    echo -e "  ❌ Error en backup de Postgres"
fi

# Backup Guardian logs
echo ""
echo "📋 Backup Guardian logs..."
if docker cp swarm_guardian:/var/log $BACKUP_DIR/guardian_logs/ 2>/dev/null; then
    echo -e "  ✅ Guardian logs: $BACKUP_DIR/guardian_logs/"
else
    echo -e "  ⚠️ No se pudieron copiar logs del Guardian"
fi

# Backup Redis state (keys)
echo ""
echo "🗄️ Backup Redis keys..."
docker exec swarm_redis redis-cli --csv KEYS "*" > $BACKUP_DIR/redis_keys.csv 2>/dev/null
echo -e "  ✅ Redis keys: $BACKUP_DIR/redis_keys.csv"

# Create manifest
echo ""
echo "📄 Creando manifiesto..."
cat > $BACKUP_DIR/manifest.json << EOF
{
  "backup_id": "$(basename $BACKUP_DIR)",
  "timestamp": "$(date -Iseconds)",
  "services": ["redis", "qdrant", "postgres", "guardian"],
  "files": {
    "redis": "redis.rdb",
    "qdrant": "qdrant/",
    "postgres": "postgres.sql",
    "guardian_logs": "guardian_logs/"
  },
  "size": "$(du -sh $BACKUP_DIR | cut -f1)"
}
EOF

echo ""
echo "========================================"
echo "✅ Backup completado: $BACKUP_DIR"
echo "📊 Tamaño: $(du -sh $BACKUP_DIR | cut -f1)"
echo ""
echo "📋 Para restaurar:"
echo "   docker cp $BACKUP_DIR/redis.rdb swarm_redis:/data/dump.rdb"
echo "   docker exec swarm_redis redis-cli CONFIG SET save ''"
echo "   docker exec swarm_redis redis-cli CONFIG SET appendonly no"
echo "   docker exec swarm_redis redis-cli FLUSHALL"
echo "   docker exec swarm_redis redis-cli --rdb /data/dump.rdb"
echo "   docker exec swarm_redis redis-cli CONFIG SET appendonly yes"
echo "   docker exec swarm_redis redis-cli CONFIG SET save '900 1 300 10 60 10000'"
echo ""
echo "   docker exec -i swarm_postgres psql -U swarm -d swarm_audit < $BACKUP_DIR/postgres.sql"