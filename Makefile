SHELL := /bin/sh
export PYTHONDONTWRITEBYTECODE := 1

PYTHON ?= python3
EXERCISE_IMPL ?= reference
PATH_EXERCISE_IMPL ?= reference
PROTOCOL_EXERCISE := exercises/protocol-inspector
PATH_EXERCISE := exercises/path-diagnosis

.PHONY: all prepare check static-check meta-check reference-check preflight \
	docs-check python-check shell-check protocol-check path-diagnosis-check \
	skeleton-check test-quality-check protocol-mutant-check workspace-safety-check \
	validator-mutant-check verify-log-safety-check runner-safety-check marker-safety-check \
	window-check observation-check docker-e2e verify clean

all: check

prepare:
	./prepare.sh

preflight:
	$(PYTHON) scripts/preflight.py

docs-check:
	$(PYTHON) scripts/validate.py

python-check:
	$(PYTHON) scripts/validate_python.py

shell-check:
	@set -eu; \
	find . -type f -name '*.sh' -not -path './.git/*' -print | sort | \
	while IFS= read -r script; do \
		printf '%s\n' "==> $$script"; \
		sh -n "$$script"; \
	done

protocol-check:
	@case "$(EXERCISE_IMPL)" in \
		skeleton|reference|workspace) ;; \
		*) printf '%s\n' 'EXERCISE_IMPL은 skeleton, reference 또는 workspace여야 합니다.' >&2; exit 2 ;; \
	esac
	@[ -d "$(PROTOCOL_EXERCISE)/$(EXERCISE_IMPL)" ] || { \
		printf '%s\n' "구현 디렉터리가 없습니다: $(PROTOCOL_EXERCISE)/$(EXERCISE_IMPL)" >&2; \
		exit 2; \
	}
	cd $(PROTOCOL_EXERCISE) && PYTHONPATH=$(EXERCISE_IMPL) $(PYTHON) -m unittest discover -s tests -v

path-diagnosis-check:
	@case "$(PATH_EXERCISE_IMPL)" in \
		skeleton|reference|broken|workspace) ;; \
		*) printf '%s\n' 'PATH_EXERCISE_IMPL은 skeleton, reference, broken 또는 workspace여야 합니다.' >&2; exit 2 ;; \
	esac
	@[ -d "$(PATH_EXERCISE)/$(PATH_EXERCISE_IMPL)" ] || { \
		printf '%s\n' "구현 디렉터리가 없습니다: $(PATH_EXERCISE)/$(PATH_EXERCISE_IMPL)" >&2; \
		exit 2; \
	}
	cd $(PATH_EXERCISE) && PYTHONPATH=$(PATH_EXERCISE_IMPL) $(PYTHON) -m unittest discover -s tests -v

skeleton-check:
	$(PYTHON) scripts/check_skeleton.py

test-quality-check:
	$(PYTHON) scripts/check_test_quality.py
	$(PYTHON) scripts/check_protocol_mutants.py

protocol-mutant-check:
	$(PYTHON) scripts/check_protocol_mutants.py

workspace-safety-check:
	$(PYTHON) scripts/test_workspace_tools.py

validator-mutant-check:
	$(PYTHON) scripts/test_validator.py

verify-log-safety-check:
	$(PYTHON) scripts/test_verify_log_safety.py

runner-safety-check:
	$(PYTHON) scripts/test-runner-safety.py

marker-safety-check:
	$(PYTHON) scripts/test_prepare_marker_safety.py

window-check:
	cd examples/window-model && $(PYTHON) -m unittest -v

observation-check:
	cd exercises/packet-observation && $(PYTHON) -m unittest discover -s tests -v

static-check: preflight docs-check python-check shell-check

meta-check: validator-mutant-check workspace-safety-check verify-log-safety-check runner-safety-check marker-safety-check

reference-check: protocol-check path-diagnosis-check window-check observation-check

check: static-check meta-check reference-check skeleton-check test-quality-check

docker-e2e:
	./exercises/linux-routing-nat/scripts/preflight.sh all
	./exercises/linux-routing-nat/scripts/run-all.sh

verify:
	./verify.sh

clean:
	find scripts examples exercises -type d -name workspace -prune -o \
		-type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
