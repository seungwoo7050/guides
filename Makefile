PYTHON ?= $(if $(wildcard .guide/python/venv/bin/python),.guide/python/venv/bin/python,python3)
PYTHON_RUN = PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B
EXERCISE_IMPL ?= reference
TEST_DIR := exercises/command-checker/tests

.PHONY: prepare verify check negative-check validator-check prepare-safety-check \
	docs-check syntax-check skeleton-check stage-contracts quality-check type-check \
	package-entrypoint-check package-check project-check install-workspace \
	reference-check exercise-check stage-01 stage-02 stage-03 stage-04 \
	stage-05 stage-06 stage-07 stage-08 stage-07-process stage-08-reports clean

prepare:
	@./prepare.sh

verify:
	@./verify.sh

negative-check:
	@./scripts/test-verify-negatives.sh

check: validator-check prepare-safety-check docs-check syntax-check stage-contracts reference-check quality-check

validator-check:
	@$(PYTHON_RUN) scripts/validate.py
	@$(PYTHON_RUN) scripts/test-validator.py

prepare-safety-check:
	@./scripts/test-prepare-safety.sh

docs-check:
	@$(PYTHON_RUN) scripts/check_docs.py

syntax-check:
	@sh -n prepare.sh verify.sh scripts/new-workspace.sh scripts/test-prepare-safety.sh
	@$(PYTHON_RUN) -c 'from pathlib import Path; files=sorted((*Path("scripts").rglob("*.py"), *Path("exercises/command-checker").rglob("*.py"))); [compile(path.read_bytes(), str(path), "exec") for path in files]; print(f"Python syntax: PASS ({len(files)} files)")'

stage-01:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_01_*.py' -v
	@$(MAKE) --no-print-directory package-entrypoint-check EXERCISE_IMPL="$(EXERCISE_IMPL)"

stage-02: stage-01
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_02_*.py' -v

stage-03: stage-02
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_03_*.py' -v

stage-04: stage-03
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_04_*.py' -v

stage-05: stage-04
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_05_*.py' -v

stage-06: stage-05
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_06_*.py' -v

stage-07: stage-06
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_07_*.py' -v

stage-08: stage-07
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_08_*.py' -v
	@$(MAKE) --no-print-directory project-check EXERCISE_IMPL="$(EXERCISE_IMPL)"

# 이전 명령과의 호환 별칭
stage-07-process: stage-07
stage-08-reports: stage-08

exercise-check:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_*.py' -v
	@$(MAKE) --no-print-directory project-check EXERCISE_IMPL="$(EXERCISE_IMPL)"

reference-check:
	@$(MAKE) --no-print-directory exercise-check EXERCISE_IMPL=reference

quality-check:
	@$(PYTHON_RUN) scripts/check_test_quality.py

type-check:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) scripts/check_type_contracts.py

package-entrypoint-check:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) scripts/check_package_install.py --entrypoint-only

package-check:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) scripts/check_package_install.py

project-check: type-check package-check

install-workspace:
	@test -x .guide/python/venv/bin/python || { printf '%s\n' '먼저 ./prepare.sh를 실행하십시오.' >&2; exit 1; }
	@test -d exercises/command-checker/workspace || { printf '%s\n' '먼저 scripts/new-workspace.sh exercises/command-checker를 실행하십시오.' >&2; exit 1; }
	@.guide/python/venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir \
		--no-index --no-deps --no-build-isolation --force-reinstall exercises/command-checker/workspace
	@printf '%s\n' '.guide/python/venv/bin/command-checker에 workspace를 설치했습니다.'

stage-contracts:
	@$(PYTHON_RUN) scripts/check_stage_contracts.py

skeleton-check:
	@$(PYTHON_RUN) scripts/check_stage_contracts.py

clean:
	@find docs exercises scripts -type d -name workspace -prune -o \
		-type d -name __pycache__ -prune -exec rm -rf -- {} +
	@find docs exercises scripts -type d -name workspace -prune -o \
		-type f \( -name '*.pyc' -o -name '*.pyo' \) -exec rm -f -- {} +
	@rm -rf -- .guide
