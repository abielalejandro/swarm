.PHONY: build up down logs health

build:
	docker compose build

up:
	docker compose up -d
	@echo "✅ Swarm started!"

down:
	docker compose down

logs:
	docker compose logs -f

health:
	@curl -s http://localhost:8000/health || echo "❌ Orchestrator not ready"
	@curl -s http://localhost:8001/health || echo "❌ Guardian not ready"
	@echo "✅ Health check complete"
