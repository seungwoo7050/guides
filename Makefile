SHELL := /bin/bash

.PHONY: check prepare verify docs-check examples-check python-check postgres-check clean

check: docs-check examples-check python-check

prepare:
	./prepare.sh

verify:
	./verify.sh

docs-check:
	python3 scripts/validate.py

examples-check:
	python3 scripts/run_examples.py

python-check:
	python3 scripts/check-exercises.py

postgres-check:
	./scripts/run-postgres-exercises.sh

clean:
	rm -rf .verify
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete
