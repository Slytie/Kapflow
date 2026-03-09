PYTEST ?= pytest -q
VALIDATOR ?= python3 scripts/validate_repo.py
RELEASE_CONFIDENCE_DB_PATH ?= $(CURDIR)/.tmp/release-confidence-gate.db
RELEASE_CONFIDENCE_DB_URL ?= sqlite:///$(RELEASE_CONFIDENCE_DB_PATH)
RELEASE_CONFIDENCE_OUTPUT_ROOT ?= $(CURDIR)/.tmp/release-confidence-gate
RELEASE_CONFIDENCE_KEY ?= release-confidence-gate
RELEASE_CONFIDENCE_OPENAI_MODE ?= mock

.PHONY: lint test schema-validate trace-validate unit contract replay acceptance runtime runtime-api security property integration integration-openai generated-check frontend-snapshots frontend-snapshots-check frontend-install frontend-typecheck frontend-test frontend-build ci-backend ci release-confidence release-confidence-validation release-confidence-demo-export release-confidence-projection-coherence release-confidence-logistics-weekly-live release-confidence-certification-manifest

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

release-confidence: release-confidence-validation release-confidence-demo-export release-confidence-projection-coherence release-confidence-logistics-weekly-live release-confidence-certification-manifest

release-confidence-validation:
	$(VALIDATOR)
	$(PYTEST) tests/contract

release-confidence-demo-export:
	$(PYTEST) tests/runtime/contracts/test_workspace_demo_export_bundle.py

release-confidence-projection-coherence:
	$(PYTEST) tests/runtime/test_projection_coherence.py

release-confidence-logistics-weekly-live:
	$(PYTEST) tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py
	$(PYTEST) tests/runtime/test_logistics_handoff_runtime.py::test_weekly_to_live_dispatch_first_golden_slice_end_to_end

release-confidence-certification-manifest:
	mkdir -p "$(CURDIR)/.tmp"
	rm -f "$(RELEASE_CONFIDENCE_DB_PATH)"
	rm -rf "$(RELEASE_CONFIDENCE_OUTPUT_ROOT)/$(RELEASE_CONFIDENCE_KEY)"
	$(PYTEST) tests/runtime/contracts/test_current_capability_certification_harness.py
	PYTHONPATH=src python3 scripts/run_current_capability_certification.py --db-url "$(RELEASE_CONFIDENCE_DB_URL)" --certification-key "$(RELEASE_CONFIDENCE_KEY)" --output-root "$(RELEASE_CONFIDENCE_OUTPUT_ROOT)" --openai-mode "$(RELEASE_CONFIDENCE_OPENAI_MODE)"
