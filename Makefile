# wizrelay — development tasks
#
# Runtime code is stdlib-only; everything here is a development dependency.

PYTHON ?= python3
PKG    := plugin/lib/wizrelay

.DEFAULT_GOAL := help
.PHONY: help install lint fmt type test unit golden e2e cov validate-plugin schema-check i18n-check docs docs-check perf all clean release

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install the package and development dependencies
	$(PYTHON) -m pip install -e ".[dev]"

lint: ## ruff check + format check + mypy
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy

fmt: ## Apply formatting and import order
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

type: ## Type-check only
	$(PYTHON) -m mypy

test: ## Run the whole test suite
	$(PYTHON) -m pytest

unit: ## Unit tests only
	$(PYTHON) -m pytest tests/unit

golden: ## Hook contract golden tests
	$(PYTHON) -m pytest tests/golden

e2e: ## CLI integration scenarios
	$(PYTHON) -m pytest tests/integration

perf: ## Performance budget tests
	$(PYTHON) -m pytest -m perf

cov: ## Coverage with the project's gates
	$(PYTHON) -m pytest --cov=wizrelay --cov-report=term-missing --cov-report=xml --cov-fail-under=80
	@$(PYTHON) scripts/check_core_coverage.py

schema-check: ## Validate every fixture against both validators
	$(PYTHON) -m pytest tests/unit/test_schemas.py -q

i18n-check: ## Assert the en and tr catalogues and templates are in step
	$(PYTHON) -m pytest tests/unit/test_i18n.py tests/unit/test_templates.py -q

docs: ## Rewrite the documentation navigation and both language indexes
	$(PYTHON) scripts/docs_nav.py

docs-check: ## Assert the documentation navigation, indexes and links are in step
	$(PYTHON) scripts/docs_nav.py --check
	$(PYTHON) -m pytest tests/unit/test_docs.py -q

validate-plugin: ## claude plugin validate --strict, skipped when the CLI is absent
	@if command -v claude >/dev/null 2>&1; then \
		claude plugin validate ./plugin --strict; \
	else \
		echo "claude CLI not found on PATH; skipping plugin validation."; \
		echo "Install Claude Code and re-run to validate the plugin."; \
	fi
	@$(PYTHON) scripts/validate_plugin_structure.py

all: lint test docs-check validate-plugin ## Everything a pull request must pass

release: ## make release VERSION=x.y.z - bump the version, cut the changelog, prepare the tag
	@test -n "$(VERSION)" || (echo "usage: make release VERSION=x.y.z" && exit 2)
	$(PYTHON) scripts/release.py $(VERSION)

clean: ## Remove build and cache artefacts
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
