.PHONY: help docker

help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development
docker:  ## Start all services in development mode
	@docker compose -f infra/docker/compose.yml up --build -d

health:  ## Check health of all services
	@echo "Checking backend health..."
	@curl -s http://localhost:8000/health || echo "Backend unhealthy"
	@echo "Checking frontend health..."
	@curl -s http://localhost:3000/ || echo "Frontend unhealthy"
	@echo "Checking ChromaDB health..."
	@curl -s http://localhost:8001/api/v1/heartbeat || echo "ChromaDB unhealthy"
