.PHONY: up down logs migrate seed test-backend test-frontend lint context audit help

help:
	@echo "Scentrix Development Makefile"
	@echo "================================"
	@echo "make up              - Start all Docker containers"
	@echo "make down            - Stop all Docker containers"
	@echo "make logs            - View Docker container logs"
	@echo "make migrate         - Run database migrations (Alembic)"
	@echo "make seed            - Seed test data into databases"
	@echo "make test-backend    - Run backend pytest suite"
	@echo "make test-frontend   - Run frontend Jest tests"
	@echo "make lint            - Run linting on all code"
	@echo "make context         - Trigger AI codebase re-mapping and context refresh"
	@echo "make audit           - Run olfactive diversity audit on dataset"
	@echo "make enrich          - Process and enrich 24k fragrance dataset with canonical vibes"

up:
	docker-compose up -d
	@echo "✓ All services started. Check logs with 'make logs'"

down:
	docker-compose down
	@echo "✓ All services stopped"

logs:
	docker-compose logs -f

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python -m scripts.seed_data

test-backend:
	docker-compose exec backend pytest --cov=app --cov-report=html

test-frontend:
	cd frontend && npm test

lint:
	@echo "Linting backend..."
	docker-compose exec backend ruff check .
	docker-compose exec backend mypy .
	@echo "Linting frontend..."
	cd frontend && npm run lint
	@echo "✓ Linting complete"

context:
	@echo "Refreshing AI Codebase Context..."
	@echo "Note: This command triggers an internal Antigravity re-scan."
	@# No-op shell command; the AI agent detects this call and runs /gsd-map-codebase
	@type .gitignore > nul
 
audit:
	docker-compose exec backend python ml/pipeline/diversity_audit.py

test-diversity:
	python internal/tools/diversity_audit.py

test-persona:
	python internal/tools/personality_test.py

enrich:
	@echo "Enriching dataset with canonical vibes..."
	docker-compose exec backend python ml/pipeline/clean.py ml/data/fra_elite_24k.json ml/data/fra_cleaned_canonical.json
	@echo "Updating Neo4j graph..."
	docker-compose exec backend python ml/pipeline/ingest.py ml/data/fra_cleaned_canonical.json
	@echo "✓ Dataset enrichment complete"

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name node_modules -exec rm -rf {} +
	find . -type d -name .next -exec rm -rf {} +
	@echo "✓ Cleanup complete"

ps:
	docker-compose ps
