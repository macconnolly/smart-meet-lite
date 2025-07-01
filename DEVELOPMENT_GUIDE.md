# Development and Testing Guide

This guide outlines best practices for developing, testing, and iterating on the Smart-Meet Lite application. Following these standards will ensure a consistent, high-quality, and efficient workflow.

---

### 1. Configuration Management with `.env`

The application uses a `.env` file for managing local configuration, which is a standard and effective practice. This allows each developer to set up their own environment variables (like API keys and database paths) without committing sensitive information to version control.

**Key Principles:**
*   **`.env.example` as a Template:** The [`.env.example`](.env.example) file serves as a blueprint for the required configuration. It should always be kept up-to-date with all the environment variables the application needs to run.
*   **`.env` for Local Overrides:** Your local `.env` file is where you provide the actual values. This file is listed in `.gitignore` and **must never be committed to the repository.**
*   **Loading Configuration:** The application should use a library like `python-dotenv` to automatically load variables from the `.env` file into the environment when the application starts.

**Setup Workflow:**
1.  If you haven't already, copy the example file:
    ```bash
    cp .env.example .env
    ```
2.  Open the `.env` file and populate it with your local configuration, such as your `OPENROUTER_API_KEY`.

---

### 2. Automated Workflows with Makefile

The [Makefile](Makefile) provides a convenient way to automate common development tasks. We will enhance it to be more robust and cross-platform (compatible with Linux, macOS, and Windows WSL).

**Key Improvements:**
*   **Modern Docker Commands:** Update `docker-compose` to the modern `docker compose` syntax.
*   **Cross-Platform Compatibility:** Replace Windows-specific commands (`if exist`, `rmdir`, `del`, `findstr`, `timeout`) with their platform-agnostic equivalents (`test -d`, `rm -rf`, `grep`, `sleep`).
*   **Code Quality Targets:** Add new targets for automatically formatting and linting the codebase.

**Proposed `Makefile` Structure:**

```makefile
.PHONY: help install setup dev run logs status stop reset clean test format lint

# ... (help text) ...

# Use python from the virtual environment
VENV_PYTHON := venv/bin/python

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup: install
	$(MAKE) download-model
	$(MAKE) init
	@echo "✅ Setup complete!"

dev:
	$(VENV_PYTHON) -m uvicorn src.api:app --reload

run:
	$(VENV_PYTHON) -m src.api

# ... (docker commands using 'docker compose') ...

# Code Quality
format:
	$(VENV_PYTHON) -m black .

lint:
	$(VENV_PYTHON) -m ruff check .

# ... (cross-platform clean and reset commands) ...
```

### 3. Code Quality and Testing

A consistent code style and automated checks are crucial for maintaining a healthy codebase.

**A. Dependencies**

We will separate production and development dependencies.

1.  [`requirements.txt`](requirements.txt): Contains only the packages needed to *run* the application.
2.  `requirements-dev.txt`: Contains packages for development, such as testing, formatting, and linting tools.

**`requirements-dev.txt`:**
```
black==24.4.2
ruff==0.4.4
pytest==8.2.0
```

**B. Formatting and Linting**

*   **`black`**: An opinionated code formatter that ensures a consistent style across the entire project.
*   **`ruff`**: An extremely fast Python linter that checks for errors, bugs, and stylistic issues.

We will add `format` and `lint` targets to the `Makefile` to make running these tools trivial.

**C. Testing Strategy**

*   **`pytest`**: The standard for testing in Python.
*   **Unit Tests:** Should be placed in a `tests/unit` directory and focus on testing individual functions and classes in isolation.
*   **Integration Tests:** Should be in `tests/integration` and test the interaction between different components (e.g., the API and the database). The existing `test_bi_system.py` is a good example of an integration test.