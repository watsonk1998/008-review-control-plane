SHELL := /bin/bash
ROOT := /Users/lucas/repos/review/008-review-control-plane

.PHONY: bootstrap dev-bridge dev-api dev-web dev test smoke verify-connectivity

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

smoke:
	$(ROOT)/scripts/smoke.sh

verify-connectivity:
	$(ROOT)/scripts/verify_connectivity.sh
