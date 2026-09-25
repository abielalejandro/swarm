docker exec swarm_redis redis-cli KEYS "session:*" | while read key; do
  data=$(docker exec swarm_redis redis-cli GET "$key")
  if [ -n "$data" ]; then
    echo "$data" | jq -r '"\(.session_id) | \(.status) | \(.current_round) rondas"'
  fi
done | column -t -s '|'