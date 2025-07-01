# ==============================================================================
# Makefile for Smart-Meet Lite
#
# Provides a consistent, cross-platform interface for common development tasks.
# ==============================================================================

# Ensure that the following commands are always executed, even if files with the same name exist.
.PHONY: help setup install dev run logs status stop reset clean test format lint

# Define variables to make commands more readable and maintainable.
VENV_PYTHON := python # This can be overridden, e.g., 'make VENV_PYTHON=venv/bin/python run'
DOCKER_COMPOSE := docker compose

# Default target executed when you run 'make' with no arguments.
help:
	@echo "Smart-Meet Lite - Development Workflow"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Core Targets:"
	@echo "  setup         - Set up the development environment (install dependencies, etc.)"
	@echo "  dev           - Start the API server in auto-reload mode for development"
	@echo "  run           - Start the API server for standard execution"
	@echo "  test          - Run the automated test suite"
	@echo ""
	@echo "Service Management:"
	@echo "  status        - Check the status of running services (API, Qdrant)"
	@echo "  logs          - Tail the logs from the Qdrant Docker container"
	@echo "  stop          - Stop and remove the Qdrant container"
	@echo "  reset         - DANGER: Stops Qdrant and deletes ALL data (vector and local DB)"
	@echo ""
	@echo "Code Quality:"
	@echo "  format        - Format all Python code using 'black'"
	@echo "  lint          - Lint all Python code using 'ruff'"
	@echo "  clean         - Remove cache files and other generated artifacts"
	@echo ""

# Default target
help:
	@echo "Smart-Meet Lite - Available commands:"
	@echo "  make setup        - Complete setup (install, download model, init DB)"
	@echo "  make run          - Start the API server"
	@echo "  make demo         - Run the business intelligence demo"
	@echo "  make test         - Test the system"
	@echo "  make clean        - Clean cache files"
	@echo ""
	@echo "Individual commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make start-qdrant - Start Qdrant container"
	@echo "  make stop-qdrant  - Stop Qdrant container"
	@echo "  make download-model - Download ONNX model"
	@echo "  make init         - Initialize database"

# Install Python dependencies
# ==============================================================================
# SETUP & EXECUTION
# ==============================================================================

# Installs all dependencies required for production and development.
install:
	@echo "Installing dependencies..."
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt
	@echo "✅ Dependencies installed."

# A comprehensive setup command for a new developer.
setup: install
	@echo "Running initial setup..."
	$(VENV_PYTHON) scripts/download_model.py
	$(VENV_PYTHON) scripts/setup.py
	@echo "✅ Setup complete! You can now run 'make dev' to start the server."

# Starts the API in development mode with auto-reloading.
dev:
	@echo "Starting API in development mode (auto-reload)..."
	@echo "URL: http://localhost:8000/docs"
	$(VENV_PYTHON) -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# Starts the API in standard mode.
run:
	@echo "Starting API server..."
	@echo "URL: http://localhost:8000/docs"
	$(VENV_PYTHON) -m uvicorn src.api:app --host 0.0.0.0 --port 8000

# ==============================================================================
# SERVICE & DATA MANAGEMENT
# ==============================================================================

# Checks the status of the Docker container and API endpoint.
status:
	@echo "--- Service Status ---"
	@echo "Qdrant Container:"
	@$(DOCKER_COMPOSE) ps | grep "qdrant" || echo "  -> Qdrant container not running."
	@echo ""
	@echo "API Endpoint:"
	@curl -s -o /dev/null -w "  -> Status: %{http_code}\n" http://localhost:8000/docs || echo "  -> API is not reachable."
	@echo "----------------------"

# Tails the logs from the Qdrant container.
logs:
	@echo "Tailing Qdrant logs... (Press Ctrl+C to exit)"
	$(DOCKER_COMPOSE) logs -f qdrant

# Stops and removes the Qdrant container.
stop:
	@echo "Stopping Qdrant container..."
	$(DOCKER_COMPOSE) down
	@echo "✅ Qdrant stopped."

# DANGER: Stops Qdrant and completely wipes all associated data.
reset:
	@echo "DANGER ZONE: This will permanently delete the Qdrant data volume and local database."
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Stopping and removing container and volume..."; \
		$(DOCKER_COMPOSE) down -v; \
		echo "Deleting local database..."; \
		rm -f data/memories.db; \
		echo "✅ Environment has been reset."; \
	else \
		echo "Reset cancelled."; \
	fi

# ==============================================================================
# CODE QUALITY & TESTING
# ==============================================================================

# Removes Python cache files and other build artifacts.
clean:
	@echo "Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@echo "✅ Cache cleaned."

# Formats the entire codebase using the 'black' formatter.
format:
	@echo "Formatting code with 'black'..."
	$(VENV_PYTHON) -m black .
	@echo "✅ Code formatted."

# Lints the codebase for errors and style issues using 'ruff'.
lint:
	@echo "Linting code with 'ruff'..."
	$(VENV_PYTHON) -m ruff check .

# Attempts to automatically fix linting issues using 'ruff'.
lint-fix:
	@echo "Attempting to auto-fix linting issues with 'ruff'..."
	$(VENV_PYTHON) -m ruff check . --fix
	@echo "✅ Linting complete."

# Runs the automated test suite using 'pytest'.
test:
	@echo "Running tests with 'pytest'..."
	$(VENV_PYTHON) -m pytest
