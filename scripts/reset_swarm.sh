#!/bin/bash

echo "⚠️  ADVERTENCIA: Esto reseteará TODO el swarm!"
echo "Se perderán:"
echo "  - Todas las negociaciones activas"
echo "  - Todos los estados emocionales de los agentes"
echo "  - Todas las pistas de auditoría"
echo "  - Todas las configuraciones de los agentes"
echo ""
read -p "¿Estás seguro? (escribe 'yes' para continuar): " confirm

if [ "$confirm" != "yes" ]; then
    echo ""
    echo "❌ Reset cancelado."
    exit 0
fi

echo ""
echo "🔄 Resetear swarm..."

# Detener todo
echo "  ⏹️ Deteniendo servicios..."
docker compose down

# Eliminar volúmenes
echo "  🗑️ Eliminando volúmenes..."
docker compose down -v

# Eliminar volúmenes huérfanos
echo "  🗑️ Limpiando volúmenes huérfanos..."
docker volume prune -f 2>/dev/null

# Limpiar imágenes no utilizadas
echo "  🗑️ Limpiando imágenes no utilizadas..."
docker image prune -f 2>/dev/null

echo ""
echo "✅ Swarm reseteado completamente!"
echo ""
echo "Para reconstruir y desplegar:"
echo "  make build"
echo "  make up"