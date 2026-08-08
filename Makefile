SHELL := /bin/bash
PYTHON ?= python3
CAPSTONE := exercises/07-verified-algorithms-capstone
STAGE ?= all
IMPL ?= reference

.PHONY: prepare verify check docs-check meta-check marker-safety-check workspace-check log-safety-check runner-safety-check checker-check \
	skeleton-check reference-check failure-check timeout-check stage-check clean

prepare:
	./prepare.sh

verify:
	./verify.sh

check: docs-check meta-check marker-safety-check workspace-check log-safety-check runner-safety-check checker-check

docs-check:
	$(PYTHON) scripts/validate.py

meta-check:
	$(PYTHON) scripts/test-validator.py

marker-safety-check:
	$(PYTHON) scripts/test-prepare-marker.py

workspace-check:
	$(PYTHON) scripts/test-workspace-tools.py

log-safety-check:
	$(PYTHON) scripts/test-verify-preflight.py

runner-safety-check:
	$(PYTHON) scripts/test-runner-safety.py

checker-check: skeleton-check reference-check failure-check timeout-check
	$(PYTHON) scripts/test-checker.py

skeleton-check:
	cd $(CAPSTONE) && $(PYTHON) check.py --impl skeleton --stage all --expect not-implemented

reference-check:
	cd $(CAPSTONE) && $(PYTHON) check.py --impl reference --stage all --expect pass

failure-check:
	cd $(CAPSTONE) && $(PYTHON) check.py --impl broken/off-by-one --stage data-structures --expect fail
	cd $(CAPSTONE) && $(PYTHON) check.py --impl broken/wrong-greedy --stage design-techniques --expect fail
	cd $(CAPSTONE) && $(PYTHON) check.py --impl broken/missed-negative-cycle --stage graphs --expect fail
	cd $(CAPSTONE) && $(PYTHON) check.py --impl broken/empty-pattern --stage strings --expect fail

timeout-check:
	cd $(CAPSTONE) && EXERCISE_TIMEOUT=1 $(PYTHON) check.py --impl broken/non-terminating --stage strings --expect timeout

stage-check:
	cd $(CAPSTONE) && $(PYTHON) check.py --impl $(IMPL) --stage $(STAGE) --expect pass

clean:
	find scripts exercises -type d -name workspace -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +
	find scripts exercises -type d -name workspace -prune -o -type f -name '*.py[co]' -exec rm -f {} +
