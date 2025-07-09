# Poetry Guide for EigenDA Python Client

This guide provides comprehensive instructions for using Poetry with the EigenDA Python client project.

## Table of Contents

1. [Installing Poetry](#installing-poetry)
2. [Basic Usage](#basic-usage)
3. [Development Workflow](#development-workflow)
4. [Managing Dependencies](#managing-dependencies)
5. [Working with Virtual Environments](#working-with-virtual-environments)
6. [Building and Publishing](#building-and-publishing)
7. [Common Commands Reference](#common-commands-reference)
8. [Troubleshooting](#troubleshooting)

## Installing Poetry

Poetry is a modern dependency management tool for Python that handles dependency resolution, virtual environments, and package building.

### Installation Methods

#### Official Installer (Recommended)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

#### Using pipx
```bash
pipx install poetry
```

#### Using pip (not recommended)
```bash
pip install --user poetry
```

### Verify Installation
```bash
poetry --version
```

## Basic Usage

### Setting Up the Project

```bash
# Clone the repository
git clone https://github.com/powerloom/eigenda-py.git
cd eigenda-py

# Install dependencies
poetry install

# Install without development dependencies
poetry install --without dev

# Install only specific groups
poetry install --only main,test
```

### Running Code

```bash
# Run a script using Poetry
poetry run python examples/minimal_client.py

# Run tests
poetry run pytest

# Run linting
poetry run flake8

# Activate the virtual environment
poetry shell
# Now you can run commands directly
python examples/minimal_client.py
pytest
exit  # to deactivate
```

## Development Workflow

### 1. Setting Up for Development

```bash
# Install all dependencies including dev
poetry install

# Install with extras (if defined)
poetry install --all-extras
```

### 2. Adding New Dependencies

```bash
# Add a production dependency
poetry add requests

# Add a development dependency
poetry add --group dev pytest-mock

# Add with version constraints
poetry add "flask>=2.0,<3.0"

# Add from git
poetry add git+https://github.com/user/repo.git

# Add local package
poetry add --path ../my-local-package
```

### 3. Updating Dependencies

```bash
# Update all dependencies
poetry update

# Update specific package
poetry update requests

# Show outdated packages
poetry show --outdated
```

### 4. Running Tests and Linting

```bash
# Run tests with coverage
poetry run pytest --cov=src --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_client_v2.py

# Run linting
poetry run flake8
poetry run mypy src/

# Run pre-commit hooks
poetry run pre-commit run --all-files
```

## Managing Dependencies

### Dependency Groups

The project uses dependency groups to organize dependencies:

- `main`: Core dependencies required for the package
- `dev`: Development tools (linting, testing, etc.)

### Lock File

Poetry uses `poetry.lock` to ensure reproducible installs:

```bash
# Regenerate lock file
poetry lock

# Install exactly what's in the lock file
poetry install --sync
```

### Exporting Dependencies

```bash
# Export to requirements.txt format
poetry export -f requirements.txt --output requirements.txt

# Export without hashes (for some CI systems)
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Export only production dependencies
poetry export -f requirements.txt --output requirements.txt --only main
```

## Working with Virtual Environments

### Environment Information

```bash
# Show environment info
poetry env info

# Show path to virtual environment
poetry env info --path

# List all environments
poetry env list
```

### Managing Python Versions

```bash
# Use specific Python version
poetry env use python3.11
poetry env use 3.11

# Use system Python
poetry env use system

# Remove an environment
poetry env remove python3.11
```

### Configuration

```bash
# Create virtual environments in project directory
poetry config virtualenvs.in-project true

# Disable virtual environment creation
poetry config virtualenvs.create false

# Show current configuration
poetry config --list
```

## Building and Publishing

### Building the Package

```bash
# Build wheel and sdist
poetry build

# This creates files in dist/
# - eigenda_py-0.1.0-py3-none-any.whl
# - eigenda_py-0.1.0.tar.gz
```

### Publishing to PyPI

```bash
# Configure PyPI token
poetry config pypi-token.pypi your-api-token

# Publish to PyPI
poetry publish

# Build and publish in one command
poetry publish --build

# Dry run (don't actually upload)
poetry publish --dry-run
```

### Publishing to Private Repository

```bash
# Add private repository
poetry config repositories.private https://private.pypi.org/simple/

# Configure credentials
poetry config http-basic.private username password

# Publish to private repository
poetry publish -r private
```

## Common Commands Reference

### Essential Commands

| Command | Description |
|---------|-------------|
| `poetry install` | Install all dependencies |
| `poetry add <package>` | Add a new dependency |
| `poetry remove <package>` | Remove a dependency |
| `poetry update` | Update dependencies |
| `poetry show` | Show installed packages |
| `poetry run <command>` | Run command in virtual environment |
| `poetry shell` | Activate virtual environment |
| `poetry build` | Build the package |
| `poetry publish` | Publish to PyPI |

### Useful Options

| Option | Description |
|--------|-------------|
| `--without dev` | Exclude dev dependencies |
| `--only main` | Install only main dependencies |
| `--dry-run` | Preview without making changes |
| `-v` or `-vvv` | Increase verbosity |
| `--no-cache` | Disable cache |

## Troubleshooting

### Common Issues

#### 1. Poetry not found after installation
```bash
# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Add to shell profile (.bashrc, .zshrc, etc.)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 2. Dependency conflicts
```bash
# Clear cache
poetry cache clear pypi --all

# Update lock file
poetry lock --no-update

# Force reinstall
poetry install --sync
```

#### 3. Virtual environment issues
```bash
# Remove all environments
poetry env remove --all

# Recreate environment
poetry install
```

#### 4. SSL/Certificate errors
```bash
# Temporarily disable SSL (not recommended for production)
poetry config certificates.pypi.org false

# Or set custom certificate
poetry config certificates.pypi.org /path/to/cert.pem
```

### Getting Help

```bash
# General help
poetry --help

# Command-specific help
poetry add --help

# Show Poetry version and environment
poetry about
```

## Integration with IDEs

### VS Code
1. Install Python extension
2. Select interpreter: `Cmd/Ctrl + Shift + P` → "Python: Select Interpreter"
3. Choose the Poetry virtual environment (usually `.venv` in project)

### PyCharm
1. Go to Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Poetry Environment"
4. PyCharm will detect and use Poetry automatically

## Best Practices

1. **Always commit `poetry.lock`**: This ensures everyone gets the same dependencies
2. **Use specific versions**: Instead of `*`, use `^1.0.0` or `~1.0.0`
3. **Separate dev dependencies**: Keep testing/linting tools in dev group
4. **Regular updates**: Run `poetry update` periodically and test
5. **Use `poetry check`**: Validates `pyproject.toml` before committing

## Advanced Usage

### Using Poetry in CI/CD

```yaml
# GitHub Actions example
- name: Install Poetry
  uses: snok/install-poetry@v1

- name: Install dependencies
  run: poetry install --no-interaction --no-root

- name: Run tests
  run: poetry run pytest
```

### Docker Integration

```dockerfile
FROM python:3.11-slim

# Install Poetry
RUN pip install poetry

# Copy project files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --without dev

# Copy application code
COPY . .

CMD ["poetry", "run", "python", "app.py"]
```

### Pre-commit Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: poetry-check
        name: Poetry check
        entry: poetry check
        language: system
        files: pyproject.toml
        pass_filenames: false
```

## Migrating from pip

If you're migrating from pip/requirements.txt:

```bash
# Import from requirements.txt
cat requirements.txt | xargs poetry add

# Or manually add each dependency
poetry add requests flask pytest

# For dev dependencies from requirements-dev.txt
cat requirements-dev.txt | xargs poetry add --group dev
```

## Conclusion

Poetry simplifies Python dependency management and provides a modern, reliable workflow for development. For the EigenDA Python client, it ensures consistent environments across all developers and deployment targets.

For more information, visit the [official Poetry documentation](https://python-poetry.org/docs/).