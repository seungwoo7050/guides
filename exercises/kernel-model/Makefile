SHELL := /bin/sh
PYTHON ?= python3
IMPL ?= workspace
CHECKPOINT ?= all

.PHONY: check verify skeleton-test reference-test failure-test checker-meta \
	workspace-test checkpoint-test fixture-smoke bytecode clean

check: skeleton-test reference-test failure-test checker-meta

verify: check fixture-smoke bytecode

skeleton-test:
	$(PYTHON) check.py skeleton

reference-test:
	$(PYTHON) check.py reference

failure-test:
	$(PYTHON) check.py failure

checker-meta:
	$(PYTHON) ../../scripts/test-checker.py

workspace-test:
	$(PYTHON) check.py implementation workspace all

checkpoint-test:
	$(PYTHON) check.py implementation $(IMPL) $(CHECKPOINT)

fixture-smoke:
	$(PYTHON) check.py reference 08-cli

bytecode:
	$(PYTHON) -m compileall -q check.py skeleton reference

clean:
	find check.py skeleton reference -type d -name __pycache__ -prune -exec rm -rf {} +
	find check.py skeleton reference -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
