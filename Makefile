.PHONY: install install-dev test lint format clean build

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies  
install-dev:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=eigenda --cov-report=term-missing

# Run linting
lint:
	flake8 src/ tests/
	mypy src/

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build package
build: clean
	python -m build

# Generate gRPC code from proto files
generate-grpc:
	python scripts/generate_grpc.py

# Run the example
example:
	python examples/minimal_client.py