#!/bin/bash

echo "📊 Estado del Swarm"
echo "========================================"

# Resumen de contenedores
echo ""
echo "📦 Contenedores:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(swarm_|NAMES)" | sed 's/^/  /'

# Uso de recursos
echo ""
echo "💻 Uso de recursos:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "(swarm_|NAME)" | sed 's/^/  /'

# Sesiones activas
echo ""
echo "📋 Sesiones activas:"
SESSIONS=$(curl -s http://localhost:8000/sessions 2>/dev/null | jq -r '.count // "N/A"')
echo "  Sesiones activas: $SESSIONS"

# Agentes activos
echo ""
echo "🤖 Agentes:"
AGENTS=$(curl -s http://localhost:8001/agents 2>/dev/null | jq -r '.count // "N/A"')
SUSPENDED=$(curl -s http://localhost:8001/agents 2>/dev/null | jq -r '.agents[] | select(.suspended==true) | .agent_id' | wc -l)
echo "  Total agentes: $AGENTS"
echo "  Suspendidos: $SUSPENDED"

echo ""
echo "========================================"