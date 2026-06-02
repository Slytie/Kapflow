PYTHON ?= python3.11
PYTEST ?= $(PYTHON) -m pytest -q
VALIDATOR ?= $(PYTHON) scripts/validate_repo.py
RELEASE_CONFIDENCE_DB_PATH ?= $(CURDIR)/.tmp/release-confidence-gate.db
RELEASE_CONFIDENCE_DB_URL ?= sqlite:///$(RELEASE_CONFIDENCE_DB_PATH)
RELEASE_CONFIDENCE_OUTPUT_ROOT ?= $(CURDIR)/.tmp/release-confidence-gate
RELEASE_CONFIDENCE_KEY ?= release-confidence-gate
RELEASE_CONFIDENCE_OPENAI_MODE ?= mock
CLEAN_SOURCE_BUNDLE_OUTPUT ?= $(CURDIR)/.tmp/companyos-clean-source-bundle.zip
RELEASE_SOURCE_BUNDLE_OUTPUT ?= $(CURDIR)/.tmp/companyos-release-source-bundle.zip
HANDOFF_SOURCE_BUNDLE_OUTPUT ?= $(CURDIR)/.tmp/companyos-handoff-source-bundle.zip
RELEASE_IMAGE_OUTPUT_ROOT ?= $(CURDIR)/.tmp/release-image
RELEASE_IMAGE_REF ?= local/onetruth-api:release-local
PREDEPLOY_BACKUP_ENV ?= lab
PREDEPLOY_BACKUP_DB_URL ?=
PREDEPLOY_BACKUP_ARTIFACT_ROOT ?=
PREDEPLOY_BACKUP_RELEASE_MANIFEST ?= $(RELEASE_IMAGE_OUTPUT_ROOT)/release_manifest.json
PREDEPLOY_BACKUP_OUTPUT ?= $(CURDIR)/.tmp/predeploy-backup/backup_manifest.json
PREDEPLOY_BACKUP_SECRET_REF_ARGS ?=
LAB_AUTH_SMOKE_DB_URL ?=
LAB_AUTH_SMOKE_JWT_ISSUER ?=
LAB_AUTH_SMOKE_JWT_AUDIENCE ?=
LAB_AUTH_SMOKE_JWT_PUBLIC_KEY_PEM_FILE ?=
LAB_AUTH_SMOKE_BEARER_TOKEN_ENV ?= LAB_VIEWER_SMOKE_TOKEN
LAB_VM_GCP_PROJECT ?=
LAB_VM_ZONE ?=
LAB_VM_INSTANCE ?=
LAB_VM_RELEASE_SOURCE_BUNDLE ?= $(RELEASE_SOURCE_BUNDLE_OUTPUT)
LAB_VM_RELEASE_MANIFEST ?= $(RELEASE_IMAGE_OUTPUT_ROOT)/release_manifest.json
LAB_VM_REMOTE_RELEASE_ROOT ?=
LAB_VM_REMOTE_DB_URL ?=
LAB_VM_REMOTE_ARTIFACT_ROOT ?=
LAB_VM_REMOTE_SERVICE_NAME ?= onetruth-api
LAB_VM_REMOTE_VIEWER_TOKEN_ENV ?= LAB_VIEWER_SMOKE_TOKEN
LAB_VM_DEPLOY_OUTPUT ?= $(CURDIR)/.tmp/lab-vm-deploy/lab_vm_deploy_report.json
LAB_VM_DEPLOY_SECRET_REF_ARGS ?=

.PHONY: lint test assurance-fast schema-validate trace-validate unit contract replay acceptance runtime runtime-api workpage-mutation-smoke security property integration integration-openai integration-openai-weekly-stage04 logistics-weekly-stage04-pilot clean-source-bundle release-source-bundle handoff-source-bundle release-image predeploy-backup-manifest lab-auth-smoke lab-vm-deploy-plan lab-vm-deploy generated-check frontend-snapshots frontend-snapshots-check frontend-install frontend-typecheck frontend-test frontend-workpages-smoke frontend-build ci-fast-backend ci-runtime-required ci-backend ci release-confidence release-confidence-validation release-confidence-demo-export release-confidence-projection-coherence release-confidence-logistics-weekly-live release-confidence-certification-manifest
.PHONY: doctor backend-lint python-lint frontend-ci

doctor:
	$(PYTHON) scripts/doctor.py --check

python-lint:
	$(PYTHON) -m ruff check --select F,E9 src tests scripts

backend-lint: assurance-fast python-lint

lint: backend-lint frontend-typecheck

test: assurance-fast contract frontend-snapshots-check unit replay acceptance runtime security property integration

assurance-fast:
	$(VALIDATOR) --domain schema --domain governance --domain metadata --domain release --domain secrets

schema-validate: assurance-fast

trace-validate:
	$(VALIDATOR) --domain traces

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

workpage-mutation-smoke:
	@$(PYTHON) -c "import importlib.util, sys; modules = ('openpyxl', 'sqlalchemy', 'yaml'); missing = [name for name in modules if importlib.util.find_spec(name) is None]; sys.exit('Missing required runtime dependencies for workpage mutation smoke: ' + ', '.join(missing) if missing else 0)"
	PYTHONPATH=src $(PYTEST) tests/runtime/api/test_workpage_mutation_smoke.py

security:
	$(PYTEST) tests/security

property:
	$(PYTEST) tests/property

integration:
	$(PYTEST) tests/integration

integration-openai:
	PYTHONPATH=src $(PYTEST) tests/integration_openai

integration-openai-weekly-stage04:
	@if [ "$${ONETRUTH_RUN_OPENAI_E2E:-0}" != "1" ] || [ "$${ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E:-0}" != "1" ]; then \
		echo "Set ONETRUTH_RUN_OPENAI_E2E=1 and ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1 before running weekly Stage04 real-network tests."; \
		exit 1; \
	fi
	PYTHONPATH=src $(PYTEST) tests/integration_openai/test_weekly_stage04_openai_real_e2e.py

logistics-weekly-stage04-pilot:
	PYTHONPATH=src $(PYTHON) scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key local-weekly-stage04 --openai-mode mock --json

release-source-bundle:
	$(PYTHON) scripts/export_clean_source_bundle.py --bundle-kind release_source_bundle --output "$(RELEASE_SOURCE_BUNDLE_OUTPUT)"

handoff-source-bundle:
	$(PYTHON) scripts/export_clean_source_bundle.py --output "$(HANDOFF_SOURCE_BUNDLE_OUTPUT)"

clean-source-bundle: release-source-bundle

release-image:
	$(PYTHON) scripts/build_release_image.py --output-root "$(RELEASE_IMAGE_OUTPUT_ROOT)" --image-ref "$(RELEASE_IMAGE_REF)" --json

predeploy-backup-manifest:
	$(PYTHON) scripts/prepare_predeploy_backup.py --environment "$(PREDEPLOY_BACKUP_ENV)" --db-url "$(PREDEPLOY_BACKUP_DB_URL)" --artifact-root "$(PREDEPLOY_BACKUP_ARTIFACT_ROOT)" --release-manifest "$(PREDEPLOY_BACKUP_RELEASE_MANIFEST)" --output "$(PREDEPLOY_BACKUP_OUTPUT)" $(PREDEPLOY_BACKUP_SECRET_REF_ARGS) --json

lab-auth-smoke:
	$(PYTHON) scripts/run_lab_auth_smoke.py --db-url "$(LAB_AUTH_SMOKE_DB_URL)" --jwt-issuer "$(LAB_AUTH_SMOKE_JWT_ISSUER)" --jwt-audience "$(LAB_AUTH_SMOKE_JWT_AUDIENCE)" --jwt-public-key-pem-file "$(LAB_AUTH_SMOKE_JWT_PUBLIC_KEY_PEM_FILE)" --bearer-token-env "$(LAB_AUTH_SMOKE_BEARER_TOKEN_ENV)" --json

lab-vm-deploy-plan:
	$(PYTHON) scripts/deploy_lab_vm.py --environment lab --gcp-project "$(LAB_VM_GCP_PROJECT)" --zone "$(LAB_VM_ZONE)" --instance "$(LAB_VM_INSTANCE)" --release-source-bundle "$(LAB_VM_RELEASE_SOURCE_BUNDLE)" --release-manifest "$(LAB_VM_RELEASE_MANIFEST)" --remote-release-root "$(LAB_VM_REMOTE_RELEASE_ROOT)" --remote-db-url "$(LAB_VM_REMOTE_DB_URL)" --remote-artifact-root "$(LAB_VM_REMOTE_ARTIFACT_ROOT)" --remote-service-name "$(LAB_VM_REMOTE_SERVICE_NAME)" --remote-viewer-token-env "$(LAB_VM_REMOTE_VIEWER_TOKEN_ENV)" --output "$(LAB_VM_DEPLOY_OUTPUT)" $(LAB_VM_DEPLOY_SECRET_REF_ARGS) --json

lab-vm-deploy:
	$(PYTHON) scripts/deploy_lab_vm.py --environment lab --gcp-project "$(LAB_VM_GCP_PROJECT)" --zone "$(LAB_VM_ZONE)" --instance "$(LAB_VM_INSTANCE)" --release-source-bundle "$(LAB_VM_RELEASE_SOURCE_BUNDLE)" --release-manifest "$(LAB_VM_RELEASE_MANIFEST)" --remote-release-root "$(LAB_VM_REMOTE_RELEASE_ROOT)" --remote-db-url "$(LAB_VM_REMOTE_DB_URL)" --remote-artifact-root "$(LAB_VM_REMOTE_ARTIFACT_ROOT)" --remote-service-name "$(LAB_VM_REMOTE_SERVICE_NAME)" --remote-viewer-token-env "$(LAB_VM_REMOTE_VIEWER_TOKEN_ENV)" --output "$(LAB_VM_DEPLOY_OUTPUT)" $(LAB_VM_DEPLOY_SECRET_REF_ARGS) --execute --confirm-lab-target --confirm-no-real-users --json

generated-check:
	$(VALIDATOR)
	$(PYTHON) scripts/generate_prototype.py --check

frontend-snapshots:
	PYTHONPATH=src $(PYTHON) scripts/export_frontend_snapshots.py

frontend-snapshots-check:
	PYTHONPATH=src $(PYTHON) scripts/export_frontend_snapshots.py --check

frontend-install:
	cd frontend && npm ci

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm run test:run

frontend-workpages-smoke:
	cd frontend && npm run test:workpages

frontend-build:
	cd frontend && npm run build

frontend-ci: frontend-typecheck frontend-test frontend-build

ci-fast-backend: backend-lint contract unit workpage-mutation-smoke security

ci-runtime-required: replay acceptance runtime frontend-snapshots-check

ci-backend: ci-fast-backend ci-runtime-required

ci: ci-backend frontend-ci

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
	PYTHONPATH=src $(PYTHON) scripts/run_current_capability_certification.py --db-url "$(RELEASE_CONFIDENCE_DB_URL)" --certification-key "$(RELEASE_CONFIDENCE_KEY)" --output-root "$(RELEASE_CONFIDENCE_OUTPUT_ROOT)" --openai-mode "$(RELEASE_CONFIDENCE_OPENAI_MODE)"
