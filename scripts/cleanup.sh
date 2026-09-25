#!/bin/bash

echo "🧹 Limpiando Swarm..."
echo "========================================"

# Detener servicios
echo "⏹️ Deteniendo servicios..."
docker compose down

# Eliminar contenedores
echo "🗑️ Eliminando contenedores..."
docker compose rm -f

# Eliminar volúmenes
echo "🗑️ Eliminando volúmenes..."
docker compose down -v

# Limpiar imágenes
echo "🗑️ Limpiando imágenes..."
docker image prune -f

# Limpiar volúmenes huérfanos
echo "🗑️ Limpiando volúmenes huérfanos..."
docker volume prune -f

# Limpiar redes
echo "🗑️ Limpiando redes huérfanas..."
docker network prune -f

echo ""
echo "✅ Limpieza completada"
echo ""
echo "Para reconstruir: make build"
echo "Para desplegar: make up"