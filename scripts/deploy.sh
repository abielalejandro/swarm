#!/bin/bash
set -e

echo "🚀 Desplegando Swarm v1.0..."
echo "========================================"

# Verificar que existe .env
if [ ! -f .env ]; then
    echo "❌ Error: .env no encontrado!"
    echo "   Ejecuta: cp .env.example .env"
    echo "   Luego edita .env con tu OPENAI_API_KEY"
    exit 1
fi

# Verificar que OPENAI_API_KEY está configurada
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-key-here" ]; then
    echo "❌ Error: OPENAI_API_KEY no está configurada en .env"
    echo "   Edita .env y agrega tu API key de OpenAI"
    exit 1
fi

echo "✅ Configuración validada"

# Construir imágenes
echo ""
echo "📦 Construyendo imágenes Docker..."
docker compose build

# Iniciar servicios
echo ""
echo "🚀 Iniciando servicios..."
docker compose up -d

# Esperar a que los servicios estén listos
echo ""
echo "⏳ Esperando que los servicios estén saludables..."
sleep 10

# Verificar salud
echo ""
echo "🔍 Verificando salud de los servicios..."
make health

echo ""
echo "✅ Despliegue completado!"
echo ""
echo "📊 Dashboard: http://localhost:8501"
echo "📡 API: http://localhost:8000/docs"
echo "⚖️ Guardian: http://localhost:8001/docs"
echo "🧠 Psychologist: http://localhost:8002/docs"
echo "🎯 Executor: http://localhost:8004/docs"
echo ""
echo "📋 Para ver logs: make logs"
echo "🛑 Para detener: make down"