docker exec swarm_redis redis-cli KEYS "session:*" | while read key; do
  data=$(docker exec swarm_redis redis-cli GET "$key")
  status=$(echo "$data" | jq -r '.status')
  if [ "$status" = "deadlocked" ] || [ "$status" = "max_rounds_reached" ]; then
    echo "❌ FALLIDA: $key"
    echo "$data" | jq '.'
    echo ""
  fi
done