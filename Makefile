SHELL := /bin/bash
PYTHON ?= python3
IMPL ?= reference
CHECKPOINT ?= all

.PHONY: prepare verify check static docs-check meta-check common-safety-check log-safety-check \
	workspace-check examples-check sanitizer-check exercise-check checker-check signal-check \
	checkpoint-check clean

prepare:
	./prepare.sh

verify:
	./verify.sh

check: docs-check meta-check common-safety-check log-safety-check workspace-check examples-check \
	sanitizer-check exercise-check signal-check

static: docs-check

docs-check:
	$(PYTHON) scripts/validate.py

meta-check:
	$(PYTHON) scripts/test-validator.py

common-safety-check:
	$(PYTHON) scripts/test-common-safety.py

log-safety-check:
	$(PYTHON) scripts/test-verify-preflight.py

workspace-check:
	$(PYTHON) scripts/test-workspace-tools.py

examples-check:
	$(MAKE) -C examples verify

sanitizer-check:
	$(MAKE) -C examples sanitizer-check

exercise-check:
	$(MAKE) -C exercises/kernel-model check

checker-check:
	$(PYTHON) scripts/test-checker.py

signal-check:
	$(PYTHON) scripts/test-verify-signal.py

checkpoint-check:
	$(MAKE) -C exercises/kernel-model checkpoint-test IMPL=$(IMPL) CHECKPOINT=$(CHECKPOINT)

clean:
	$(MAKE) -C examples clean
	$(MAKE) -C exercises/kernel-model clean
	find scripts exercises/kernel-model/reference exercises/kernel-model/skeleton \
		-type d -name __pycache__ -prune -exec rm -rf {} +
