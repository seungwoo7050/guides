SHELL := /bin/bash

.PHONY: check prepare verify docs-check validator-check examples-check python-check postgres-check clean

check: docs-check validator-check examples-check python-check

prepare:
	./prepare.sh

verify:
	./verify.sh

docs-check:
	python3 scripts/validate.py

validator-check:
	python3 scripts/test-validator.py
	python3 scripts/test-workspace-tools.py

examples-check:
	python3 scripts/run_examples.py

python-check:
	python3 scripts/check-exercises.py

postgres-check:
	./scripts/run-postgres-exercises.sh

clean:
	./scripts/clean-generated.sh
