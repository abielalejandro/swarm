#!/bin/bash

echo "📋 TODAS LAS SESIONES"
echo "======================"
echo ""

docker exec swarm_redis redis-cli KEYS "session:*" | while read key; do
  data=$(docker exec swarm_redis redis-cli GET "$key")

  if [ -n "$data" ]; then
    session_id=$(echo "$data" | jq -r '.session_id // "N/A"')
    status=$(echo "$data" | jq -r '.status // "N/A"')
    rounds=$(echo "$data" | jq -r '.current_round // 0')
    created=$(echo "$data" | jq -r '.created_at // "N/A"')

    echo "📌 $session_id"
    echo "   Estado: $status"
    echo "   Rondas: $rounds"
    echo "   Creada: $created"

    # Ver si tiene contrato
    contract=$(echo "$data" | jq -r '.final_contract // null')
    if [ "$contract" != "null" ] && [ "$contract" != "" ]; then
      echo "   ✅ Contrato: Si"
    else
      echo "   ❌ Contrato: No"
    fi

    echo ""
  fi
done

echo "======================"
echo "✅ Fin del listado"