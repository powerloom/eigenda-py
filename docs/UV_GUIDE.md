# UV Package Manager Guide for EigenDA Python Client

## Overview

UV is a modern, extremely fast Python package manager written in Rust. It serves as a drop-in replacement for pip and pip-tools, while also providing advanced features similar to Poetry. UV is significantly faster than traditional Python package managers, often 10-100x faster for dependency resolution and installation.

## Installation

### Using the official installer (Recommended)

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Using pip

```bash
pip install uv
```

### Using Homebrew (macOS)

```bash
brew install uv
```

## Basic Usage with EigenDA Client

### Setting up the project

```bash
# Clone the repository
git clone https://github.com/powerloom/eigenda-py.git
cd eigenda-py/python-client

# Install all dependencies (creates a virtual environment automatically)
uv sync

# Install with development dependencies
uv sync --dev

# Install with optional extras (docs, notebook)
uv sync --extra docs --extra notebook
```

### Managing the virtual environment

UV automatically creates and manages a virtual environment in `.venv`:

```bash
# Activate the virtual environment (optional, UV handles this automatically)
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Run commands using UV (no activation needed)
uv run python examples/minimal_client.py

# Run tests
uv run pytest

# Run with specific Python version
uv run --python 3.11 python examples/full_example.py
```

### Common UV Commands

```bash
# Install dependencies from pyproject.toml and uv.lock
uv sync

# Add a new dependency
uv add requests

# Add a development dependency
uv add --dev pytest-benchmark

# Remove a dependency
uv remove requests

# Update all dependencies
uv lock --upgrade

# Update a specific dependency
uv lock --upgrade-package web3

# Show installed packages
uv pip list

# Create requirements.txt for pip compatibility
uv pip compile pyproject.toml -o requirements.txt

# Install from requirements.txt
uv pip install -r requirements.txt
```

## Working with the EigenDA Client

### Running examples

```bash
# Set your environment variables
export EIGENDA_PRIVATE_KEY="your_private_key_here"

# Run examples using UV
uv run python examples/minimal_client.py
uv run python examples/full_example.py
uv run python examples/check_payment_vault.py
```

### Running tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=eigenda --cov-report=html

# Run specific test file
uv run pytest tests/test_client_v2.py

# Run tests in parallel
uv run pytest -n auto
```

### Code quality checks

```bash
# Format code with black
uv run black src/ tests/ examples/

# Sort imports with isort
uv run isort src/ tests/ examples/

# Run linting with flake8
uv run flake8 src/ tests/ examples/

# Type checking with mypy
uv run mypy src/
```

## Advanced Features

### Using different Python versions

UV can manage multiple Python versions:

```bash
# Use specific Python version
uv sync --python 3.9

# Run with specific Python version
uv run --python 3.11 python script.py
```

### Lock file management

The `uv.lock` file ensures reproducible builds:

```bash
# Generate/update lock file
uv lock

# Sync dependencies from lock file
uv sync

# Upgrade all dependencies
uv lock --upgrade

# Upgrade specific package
uv lock --upgrade-package web3
```

### Caching

UV uses aggressive caching for faster installs:

```bash
# Clear UV cache
uv cache clean

# Show cache info
uv cache dir
```

## Comparison with Poetry

| Feature | UV | Poetry |
|---------|-----|---------|
| **Installation Speed** | 10-100x faster | Baseline |
| **Dependency Resolution** | Very fast (Rust-based) | Slower (Python-based) |
| **Lock File** | `uv.lock` | `poetry.lock` |
| **Virtual Environment** | Automatic in `.venv` | Configurable location |
| **PEP Standards** | Full PEP 517/518/621 support | Full support |
| **Command Syntax** | Similar to pip | Custom syntax |
| **Python Version Management** | Built-in | Requires pyenv |

## Migration from Poetry

If you're migrating from Poetry:

1. **Lock file**: UV will read `pyproject.toml` and generate its own `uv.lock`
2. **Commands mapping**:
   - `poetry install` → `uv sync`
   - `poetry add package` → `uv add package`
   - `poetry remove package` → `uv remove package`
   - `poetry run python` → `uv run python`
   - `poetry shell` → `source .venv/bin/activate`
   - `poetry lock` → `uv lock`
   - `poetry update` → `uv lock --upgrade`

## Troubleshooting

### Common Issues

1. **Virtual environment not found**
   ```bash
   # UV creates .venv automatically on first sync
   uv sync
   ```

2. **Permission errors**
   ```bash
   # Use user installation
   uv sync --python-preference system
   ```

3. **Dependency conflicts**
   ```bash
   # Clear cache and re-lock
   uv cache clean
   uv lock --refresh
   uv sync
   ```

4. **Import errors when running scripts**
   ```bash
   # Always use uv run to ensure proper environment
   uv run python script.py
   ```

## Best Practices

1. **Always commit `uv.lock`**: This ensures reproducible builds across all environments
2. **Use `uv run`**: This ensures the correct virtual environment is used
3. **Regular updates**: Run `uv lock --upgrade` periodically to get security updates
4. **CI/CD Integration**: UV works great in CI/CD pipelines due to its speed

## Example Workflow

Here's a complete workflow for developing with the EigenDA client:

```bash
# 1. Clone and setup
git clone https://github.com/powerloom/eigenda-py.git
cd eigenda-py/python-client

# 2. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --dev

# 4. Set environment variables
export EIGENDA_PRIVATE_KEY="your_key_here"

# 5. Run tests to verify setup
uv run pytest tests/test_mock_client.py

# 6. Try an example
uv run python examples/minimal_client.py

# 7. Make changes and test
# ... edit files ...
uv run black src/
uv run pytest

# 8. Add a new dependency if needed
uv add some-package

# 9. Update lock file
uv lock
```

## Performance Benefits

UV's performance advantages are particularly noticeable in:
- CI/CD pipelines (faster builds)
- Docker containers (smaller images, faster builds)
- Development iterations (instant package operations)
- Large projects with many dependencies

For the EigenDA client with its ~50 dependencies, UV typically:
- Resolves dependencies in <1 second (vs 30+ seconds with pip)
- Installs packages in 5-10 seconds (vs 1-2 minutes with pip)
- Updates lock files instantly (vs minutes with Poetry)

## Additional Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV Benchmarks](https://github.com/astral-sh/uv#benchmarks)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
- [Python Packaging Guide](https://packaging.python.org/)