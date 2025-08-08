.PHONY: install install-dev test lint format clean build

# Install production dependencies
install:
	uv sync

# Install development dependencies
install-dev:
	uv sync --all-extras

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v --cov=eigenda --cov-report=term-missing

# Run linting
lint:
	uv run flake8 src/ tests/
	uv run mypy src/

# Format code
format:
	uv run black src/ tests/
	uv run isort src/ tests/

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build package
build: clean
	uv build

# Generate gRPC code from proto files
generate-grpc:
	uv run python scripts/generate_grpc.py

# Run the example
example:
	uv run python examples/minimal_client.py