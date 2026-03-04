PYTEST ?= pytest -q
VALIDATOR ?= python3 scripts/validate_repo.py

.PHONY: lint test schema-validate trace-validate unit contract replay acceptance runtime runtime-api security property integration integration-openai generated-check frontend-snapshots frontend-snapshots-check frontend-install frontend-typecheck frontend-test frontend-build ci-backend ci

lint: schema-validate contract

test: schema-validate contract frontend-snapshots-check unit replay acceptance runtime security property integration

schema-validate:
	$(VALIDATOR) --schemas-only

trace-validate:
	$(VALIDATOR) --traces-only

unit:
	$(PYTEST) tests/unit

contract:
	$(PYTEST) tests/contract

replay:
	$(PYTEST) tests/replay

acceptance: trace-validate
	$(PYTEST) tests/acceptance

runtime:
	PYTHONPATH=src $(PYTEST) tests/runtime

runtime-api:
	PYTHONPATH=src $(PYTEST) tests/runtime/api

security:
	$(PYTEST) tests/security

property:
	$(PYTEST) tests/property

integration:
	$(PYTEST) tests/integration

integration-openai:
	PYTHONPATH=src $(PYTEST) tests/integration_openai

generated-check:
	$(VALIDATOR)
	python3 scripts/generate_prototype.py --check

frontend-snapshots:
	PYTHONPATH=src python3 scripts/export_frontend_snapshots.py

frontend-snapshots-check:
	PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check

frontend-install:
	cd frontend && npm ci

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm run test:run

frontend-build:
	cd frontend && npm run build

ci-backend: schema-validate contract replay acceptance runtime frontend-snapshots-check

ci: ci-backend frontend-typecheck frontend-test
