#!/bin/bash

echo "🔍 Verificando salud del Swarm..."
echo "========================================"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar servicios Docker
echo ""
echo "📦 Servicios Docker:"
services=("orchestrator" "guardian" "psychologist" "meta_psychologist" "executor" "dashboard")

for service in "${services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "swarm_$service"; then
        echo -e "  ${GREEN}✅${NC} $service está funcionando"
    else
        echo -e "  ${RED}❌${NC} $service NO está funcionando"
    fi
done

# Verificar Redis
echo ""
echo "🗄️ Redis:"
if docker exec swarm_redis redis-cli ping > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Redis está saludable"
else
    echo -e "  ${RED}❌${NC} Redis no responde"
fi

# Verificar Qdrant
echo ""
echo "🔍 Qdrant:"
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Qdrant está saludable"
else
    echo -e "  ${RED}❌${NC} Qdrant no responde"
fi

# Verificar Postgres
echo ""
echo "🐘 Postgres:"
if docker exec swarm_postgres pg_isready -U swarm > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Postgres está saludable"
else
    echo -e "  ${RED}❌${NC} Postgres no responde"
fi

# Verificar APIs
echo ""
echo "🌐 APIs:"

# Orchestrator
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Orchestrator API (8000)"
else
    echo -e "  ${RED}❌${NC} Orchestrator API (8000)"
fi

# Guardian
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Guardian API (8001)"
else
    echo -e "  ${RED}❌${NC} Guardian API (8001)"
fi

# Psychologist
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Psychologist API (8002)"
else
    echo -e "  ${RED}❌${NC} Psychologist API (8002)"
fi

# Meta-Psychologist
if curl -s http://localhost:8003/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Meta-Psychologist API (8003)"
else
    echo -e "  ${RED}❌${NC} Meta-Psychologist API (8003)"
fi

# Executor
if curl -s http://localhost:8004/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Executor API (8004)"
else
    echo -e "  ${RED}❌${NC} Executor API (8004)"
fi

# Dashboard
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Dashboard (8501)"
else
    echo -e "  ${RED}❌${NC} Dashboard (8501)"
fi

echo ""
echo "========================================"
echo "✅ Health check completado"