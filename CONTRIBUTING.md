# Contributing to ai-lib-python

Thank you for your interest in contributing to ai-lib-python! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ai-lib-python.git
   cd ai-lib-python
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/hiddenpath/ai-lib-python.git
   ```

## Development Setup

### Requirements

- Python 3.10 or higher
- pip (latest version recommended)

### Installation

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run tests
pytest

# Run type checking
mypy src

# Run linting
ruff check src tests
```

## Making Changes

### Branching

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Keep your branch up to date**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(client): add retry configuration to AiClientBuilder
fix(pipeline): handle empty SSE events correctly
docs: update README with streaming examples
test(resilience): add circuit breaker state transition tests
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_resilience.py

# Run specific test class
pytest tests/unit/test_resilience.py::TestRetryPolicy

# Run with coverage
pytest --cov=src/ai_lib_python --cov-report=html
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Use pytest fixtures for common setup
- Use `@pytest.mark.asyncio` for async tests

Example:
```python
class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_default_config_has_three_retries(self) -> None:
        """Test that default config has 3 retries."""
        config = RetryConfig()
        assert config.max_retries == 3

    @pytest.mark.asyncio
    async def test_execute_retries_on_server_error(self) -> None:
        """Test that execute retries on 500 errors."""
        policy = RetryPolicy(RetryConfig(max_retries=2))
        attempts = [0]

        async def flaky_op() -> str:
            attempts[0] += 1
            if attempts[0] < 2:
                raise RemoteError("Error", status_code=500)
            return "success"

        result = await policy.execute(flaky_op)
        assert result.success
        assert attempts[0] == 2
```

## Code Style

### Formatting

We use [ruff](https://github.com/astral-sh/ruff) for formatting and linting:

```bash
# Format code
ruff format src tests

# Check linting
ruff check src tests

# Auto-fix linting issues
ruff check --fix src tests
```

### Type Hints

All code must have type hints:

```python
# Good
def calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
    ...

# Bad
def calculate_delay(self, attempt, retry_after=None):
    ...
```

Run mypy to check types:
```bash
mypy src
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
    """Calculate delay for a retry attempt.

    Implements exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-based)
        retry_after: Optional retry-after hint from server

    Returns:
        Delay in seconds

    Example:
        >>> policy = RetryPolicy(RetryConfig())
        >>> delay = policy.calculate_delay(0)
        >>> assert delay >= 0
    """
```

### Imports

Organize imports in this order:
1. Standard library
2. Third-party packages
3. Local imports

Use `TYPE_CHECKING` for type-only imports:

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from ai_lib_python.errors import TransportError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
```

## Pull Request Process

1. **Ensure all tests pass**:
   ```bash
   pytest
   ```

2. **Ensure code is formatted and linted**:
   ```bash
   ruff format src tests
   ruff check src tests
   ```

3. **Ensure types are correct**:
   ```bash
   mypy src
   ```

4. **Update documentation** if needed

5. **Create the pull request**:
   - Use a descriptive title
   - Reference any related issues
   - Describe what changes were made and why

6. **Address review feedback**

7. **Squash commits** if requested

### PR Checklist

- [ ] Tests pass locally
- [ ] Code is formatted with ruff
- [ ] No new linting errors
- [ ] Type hints are complete
- [ ] Docstrings are updated
- [ ] CHANGELOG.md is updated (for features/fixes)
- [ ] Documentation is updated (if needed)

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.1.0`
4. Push the tag: `git push origin v0.1.0`
5. GitHub Actions will build and publish to PyPI

## Questions?

If you have questions:
- Open a [GitHub Discussion](https://github.com/hiddenpath/ai-lib-python/discussions)
- Check existing issues for similar questions
- Read the documentation in `/docs`

Thank you for contributing!
