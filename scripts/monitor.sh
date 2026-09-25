#!/bin/bash

echo "📊 Monitoreo continuo del Swarm"
echo "========================================"
echo ""
echo "Presiona Ctrl+C para salir"
echo ""

while true; do
    clear
    echo "📊 Swarm Monitor - $(date)"
    echo "========================================"
    
    # Número de contenedores en ejecución
    RUNNING=$(docker ps --format '{{.Names}}' | grep -c "swarm_")
    echo "🟢 Contenedores activos: $RUNNING/11"
    
    # Sesiones activas
    SESSIONS=$(curl -s http://localhost:8000/sessions 2>/dev/null | jq -r '.count // "0"')
    echo "📋 Sesiones activas: $SESSIONS"
    
    # Agentes activos
    AGENTS=$(curl -s http://localhost:8001/agents 2>/dev/null | jq -r '.count // "0"')
    SUSPENDED=$(curl -s http://localhost:8001/agents 2>/dev/null | jq -r '.agents[] | select(.suspended==true) | .agent_id' | wc -l)
    echo "🤖 Agentes: $AGENTS ($SUSPENDED suspendidos)"
    
    # Última auditoría
    echo ""
    echo "📋 Últimas auditorías:"
    curl -s http://localhost:8003/audits?limit=3 2>/dev/null | jq -r '.audits[] | "  \(.timestamp) - \(.recommendation)"' 2>/dev/null || echo "  No hay auditorías recientes"
    
    # Últimas ejecuciones
    echo ""
    echo "⚡ Últimas ejecuciones:"
    curl -s http://localhost:8004/executions 2>/dev/null | jq -r '.executions[0:3][] | "  \(.contract_id) - \(.status)"' 2>/dev/null || echo "  No hay ejecuciones recientes"
    
    echo ""
    echo "========================================"
    echo "Actualizando en 5 segundos..."
    sleep 5
done