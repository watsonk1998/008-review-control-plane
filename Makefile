SHELL := /bin/bash
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

.PHONY: bootstrap dev-bridge dev-api dev-web dev test test-review-unit test-review-integration smoke verify-connectivity eval-review eval-review-ablations eval-review-cross-pack eval-review-cross-model eval-review-replay

bootstrap:
	$(ROOT)/scripts/bootstrap.sh

dev-bridge:
	$(ROOT)/scripts/dev.sh bridge

dev-api:
	$(ROOT)/scripts/dev.sh api

dev-web:
	$(ROOT)/scripts/dev.sh web

dev:
	$(ROOT)/scripts/dev.sh all

test:
	cd $(ROOT)/apps/api && . .venv/bin/activate && pytest -q
	cd $(ROOT)/apps/web && npm run lint && npm run build

test-review-unit:
	cd $(ROOT)/apps/api && . .venv/bin/activate && pytest -q tests/test_structured_review.py

test-review-integration:
	cd $(ROOT)/apps/api && . .venv/bin/activate && pytest -q tests/test_runtime.py -k structured_review

eval-review:
	cd $(ROOT)/apps/api && . .venv/bin/activate && python -m src.review.evaluation.harness

eval-review-ablations:
	cd $(ROOT)/apps/api && . .venv/bin/activate && python -m src.review.evaluation.harness --mode ablations

eval-review-cross-pack:
	cd $(ROOT)/apps/api && . .venv/bin/activate && python -m src.review.evaluation.harness --mode cross-pack

eval-review-cross-model:
	cd $(ROOT)/apps/api && . .venv/bin/activate && python -m src.review.evaluation.harness --mode cross-model

eval-review-replay:
	cd $(ROOT)/apps/api && . .venv/bin/activate && python -m src.review.evaluation.harness --mode replay $(if $(CASE_ID),--case-id $(CASE_ID),) $(if $(CASE_VERSION),--case-version $(CASE_VERSION),) $(if $(DOC_TYPE),--doc-type $(DOC_TYPE),) $(if $(OUTPUT_DIR),--output-dir $(OUTPUT_DIR),)

smoke:
	$(ROOT)/scripts/smoke.sh

verify-connectivity:
	$(ROOT)/scripts/verify_connectivity.sh
