#!/usr/bin/env bash
set -euo pipefail

# Code Documentation Assistant - Environment Setup Script
# This script sets up the development environment for the project

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS=Linux;;
        Darwin*)    OS=Mac;;
        CYGWIN*)    OS=Cygwin;;
        MINGW*)     OS=MinGw;;
        *)          OS="UNKNOWN:${unameOut}"
    esac
}

# Install Python dependencies
install_backend_deps() {
    log_info "Installing backend dependencies..."

    if ! command_exists uv; then
        log_warn "uv not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    cd backend
    uv sync --all-extras
    log_success "Backend dependencies installed"

    cd "$PROJECT_ROOT"
}

# Install Node.js dependencies
install_frontend_deps() {
    log_info "Installing frontend dependencies..."

    if ! command_exists bun; then
        log_warn "bun not found. Installing bun..."
        curl -fsSL https://bun.sh/install | bash
    fi

    if [ -d "frontend" ]; then
        cd frontend
        bun install
        log_success "Frontend dependencies installed"
    else
        log_warn "Frontend directory not found. Skipping..."
    fi

    cd "$PROJECT_ROOT"
}

# Install Temporal dependencies
install_temporal_deps() {
    log_info "Installing Temporal worker dependencies..."

    if [ -d "temporal" ]; then
        cd temporal
        uv sync --all-extras
        log_success "Temporal dependencies installed"
    else
        log_warn "Temporal directory not found. Skipping..."
    fi

    cd "$PROJECT_ROOT"
}

# Start ChromaDB (local vector store)
start_chromadb() {
    log_info "Setting up ChromaDB..."

    # Check if ChromaDB is already running
    if pgrep -f "chroma-run" &> /dev/null; then
        log_warn "ChromaDB is already running"
        return
    fi

    # Create data directory
    mkdir -p data/chromadb

    # Start ChromaDB in background
    log_info "Starting ChromaDB..."
    cd backend
    uv run chroma-run --host localhost --port 8000 --path ../data/chromadb &
    CHROMA_PID=$!
    echo $CHROMA_PID > ../data/chromadb.pid

    # Wait for ChromaDB to start
    log_info "Waiting for ChromaDB to start..."
    sleep 5

    if pgrep -f "chroma-run" &> /dev/null; then
        log_success "ChromaDB started (PID: $CHROMA_PID)"
        log_info "ChromaDB running at http://localhost:8000"
    else
        log_error "Failed to start ChromaDB"
    fi

    cd "$PROJECT_ROOT"
}

# Start Temporal server
start_temporal() {
    log_info "Setting up Temporal..."

    # Check if Temporal is already running
    if pgrep -f "temporal-server" &> /dev/null; then
        log_warn "Temporal server is already running"
        return
    fi

    # Check if temporal-cli is installed
    if ! command_exists temporal; then
        log_warn "temporal-cli not found. Installing..."
        detect_os
        if [[ "$OS" == "Mac" ]]; then
            brew install temporal
        elif [[ "$OS" == "Linux" ]]; then
            curl -sSL https://temporal.io/cli-install.sh | sh
        else
            log_error "Cannot install temporal-cli on $OS"
            return
        fi
    fi

    # Create data directory
    mkdir -p data/temporal

    # Start Temporal server in background
    log_info "Starting Temporal server..."
    temporal server start-dev --db-filename ../data/temporal/temporal.db &
    TEMPORAL_PID=$!
    echo $TEMPORAL_PID > data/temporal.pid

    # Wait for Temporal to start
    log_info "Waiting for Temporal to start..."
    sleep 5

    if pgrep -f "temporal-server" &> /dev/null; then
        log_success "Temporal server started (PID: $TEMPORAL_PID)"
        log_info "Temporal UI available at http://localhost:7233"
    else
        log_error "Failed to start Temporal server"
    fi
}

# Setup environment variables
setup_env() {
    log_info "Setting up environment variables..."

    if [ ! -f "backend/.env" ]; then
        cat > backend/.env << EOF
# API Keys (required for production)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
JINA_API_KEY=your_jina_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Service Configuration
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# Logging
LOG_LEVEL=info
ENVIRONMENT=development
EOF
        log_success "Created backend/.env file"
        log_warn "Please update the API keys in backend/.env"
    else
        log_info "backend/.env already exists. Skipping..."
    fi
}

# Run database migrations (if applicable)
run_migrations() {
    log_info "Running database migrations..."

    # For MVP, no migrations yet
    log_info "No migrations to run for MVP"
}

# Print setup summary
print_summary() {
    echo ""
    echo "============================================="
    log_success "Setup Complete!"
    echo "============================================="
    echo ""
    echo "Environment:"
    echo "  - Backend: Python 3.12+ with uv"
    echo "  - Frontend: TypeScript with Bun"
    echo "  - Temporal: Workflow orchestration"
    echo "  - ChromaDB: Vector database"
    echo ""
    echo "Quick Start Commands:"
    echo "  Backend:   cd backend && uvicorn app.main:app --reload"
    echo "  Frontend:  cd frontend && bun run dev"
    echo "  Temporal:  cd temporal && python worker.py"
    echo ""
    echo "Services Running:"
    if pgrep -f "chroma-run" &> /dev/null; then
        echo "  ✓ ChromaDB: http://localhost:8000"
    else
        echo "  ✗ ChromaDB: Not running (start with: ./scripts/setup.sh start-chromadb)"
    fi

    if pgrep -f "temporal-server" &> /dev/null; then
        echo "  ✓ Temporal: http://localhost:7233"
    else
        echo "  ✗ Temporal: Not running (start with: ./scripts/setup.sh start-temporal)"
    fi
    echo ""
    echo "Next Steps:"
    echo "  1. Update API keys in backend/.env"
    echo "  2. Start the backend server"
    echo "  3. Start the frontend dev server"
    echo "  4. Start the Temporal worker (for background processing)"
    echo ""
}

# Main setup flow
main() {
    echo "============================================"
    echo "  Code Documentation Assistant - Setup"
    echo "============================================"
    echo ""

    # Parse arguments
    case "${1:-}" in
        "deps"|"install")
            install_backend_deps
            install_frontend_deps
            install_temporal_deps
            ;;
        "start-chromadb")
            start_chromadb
            exit 0
            ;;
        "start-temporal")
            start_temporal
            exit 0
            ;;
        "env"|"environment")
            setup_env
            exit 0
            ;;
        "")
            # Full setup
            detect_os
            log_info "Detected OS: $OS"
            echo ""

            install_backend_deps
            install_frontend_deps
            install_temporal_deps
            setup_env
            start_chromadb
            start_temporal
            run_migrations
            print_summary
            ;;
        *)
            echo "Usage: $0 [deps|start-chromadb|start-temporal|env|environment]"
            echo ""
            echo "Commands:"
            echo "  deps               Install all dependencies"
            echo "  start-chromadb     Start ChromaDB server"
            echo "  start-temporal     Start Temporal server"
            echo "  env, environment   Setup environment files"
            echo "  (no args)          Full setup"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
