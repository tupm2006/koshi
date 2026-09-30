.PHONY: test-unit test-api test-e2e test-perf test-coverage test-all

test-unit:
	cd source_code/frontend && npm run test:unit

test-api:
	python -m pytest source_code/backend/tests

test-e2e:
	cd source_code/frontend && npm run test:e2e

test-perf:
	cd source_code/frontend && npm run test:perf

test-coverage:
	cd source_code/frontend && npm run test:coverage
	python -m pytest --cov=source_code/backend/app --cov-report=term --cov-report=html:docs/testing/coverage-backend source_code/backend/tests

test-all: test-unit test-api test-e2e
