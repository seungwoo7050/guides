SHELL := /bin/sh

PYTHON ?= python3
EXERCISE_IMPL ?= skeleton

EXAMPLES := \
	examples/layout-benchmark \
	examples/branch-benchmark \
	examples/vectorization-report \
	examples/false-sharing

BENCHMARKS := \
	examples/layout-benchmark \
	examples/branch-benchmark \
	examples/false-sharing

.PHONY: all prepare check verify docs-check exercise-check examples-check \
	test-quality stage-01 stage-02 stage-03 stage-04 stage-05 stage-06 \
	stage-07 stage-08 stage-09 stage-10 vector-report benchmark clean

all: check

prepare:
	@./prepare.sh

check: docs-check exercise-check test-quality examples-check
	@printf '\ncomputer-architecture: 빠른 검사를 모두 통과했습니다\n'

docs-check:
	@$(PYTHON) scripts/validate_docs.py

exercise-check:
	@PYTHONDONTWRITEBYTECODE=1 $(MAKE) -C exercises/processor-model check

test-quality:
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/test-validator.py
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/test-prepare-marker.py
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/test-runner-safety.py
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/test-workspace-tools.py
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/test-verify-preflight.py
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/test-exercise-quality.py

examples-check:
	@set -eu; \
	for dir in $(EXAMPLES); do \
		printf '\n==> %s\n' "$$dir"; \
		$(MAKE) -C "$$dir" check; \
	done

verify:
	@./verify.sh

stage-01 stage-02 stage-03 stage-04 stage-05 stage-06 stage-07 stage-08 stage-10:
	@PYTHONDONTWRITEBYTECODE=1 $(MAKE) -C exercises/processor-model $@ EXERCISE_IMPL="$(EXERCISE_IMPL)"

stage-09: vector-report
	@printf 'stage-09: SIMD 결과와 compiler 보고서를 검증했습니다\n'

vector-report:
	@$(MAKE) -C examples/vectorization-report report

benchmark:
	@set -eu; \
	for dir in $(BENCHMARKS); do \
		printf '\n==> %s (benchmark)\n' "$$dir"; \
		$(MAKE) -C "$$dir" benchmark; \
	done

clean:
	@$(MAKE) -C exercises/processor-model clean
	@set -eu; \
	for dir in $(EXAMPLES); do \
		$(MAKE) -C "$$dir" clean >/dev/null 2>&1 || true; \
	done
	@find . -type d \( -name .guide -o -name workspace \) -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type d \( -name .guide -o -name workspace \) -prune -o -type f -name '*.py[co]' -exec rm -f {} +
