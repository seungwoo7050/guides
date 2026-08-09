.PHONY: prepare check test-reference test-starter-contract test-mutants test-capstone verify clean

PYTHON := python3
RUNNER := exercises/10-capstone-local-coding-agent/tests/run.py
PYTHON_ENV := PYTHONDONTWRITEBYTECODE=1

prepare:
	./prepare.sh

check:
	$(PYTHON_ENV) $(PYTHON) -B scripts/check_docs.py
	$(PYTHON_ENV) $(PYTHON) -B scripts/check_contracts.py
	$(PYTHON_ENV) $(PYTHON) -B scripts/check_repository.py

test-reference:
	$(PYTHON_ENV) $(PYTHON) -B $(RUNNER) --implementation reference --stage all

test-starter-contract:
	$(PYTHON_ENV) $(PYTHON) -B $(RUNNER) --implementation starter --stage all --expect-incomplete

test-mutants:
	$(PYTHON_ENV) $(PYTHON) -B $(RUNNER) --implementation mutants --stage all

test-capstone:
	$(PYTHON_ENV) $(PYTHON) -B $(RUNNER) --implementation reference --stage capstone

verify:
	./verify.sh

clean:
	rm -rf -- .guide
