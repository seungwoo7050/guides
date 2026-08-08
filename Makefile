PYTHON ?= $(if $(wildcard .guide/python/venv/bin/python),.guide/python/venv/bin/python,python3)
PYTHON_RUN = PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B
EXERCISE_IMPL ?= reference
TEST_DIR := exercises/command-checker/tests

.PHONY: prepare verify check negative-check validator-check prepare-safety-check \
	docs-check syntax-check skeleton-check quality-check \
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

stage-02:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_02_*.py' -v

stage-03:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_03_*.py' -v

stage-04:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_04_*.py' -v

stage-05:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_05_*.py' -v

stage-06:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_06_*.py' -v

stage-07:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_07_*.py' -v

stage-08:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_08_*.py' -v

# 이전 명령과의 호환 별칭
stage-07-process: stage-07
stage-08-reports: stage-08

exercise-check:
	@EXERCISE_IMPL="$(EXERCISE_IMPL)" $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_*.py' -v

reference-check:
	@$(MAKE) --no-print-directory exercise-check EXERCISE_IMPL=reference

quality-check:
	@$(PYTHON_RUN) scripts/check_test_quality.py

stage-contracts:
	@$(PYTHON_RUN) scripts/check_stage_contracts.py

skeleton-check:
	@log=$$(mktemp "$${TMPDIR:-/tmp}/guide-python-skeleton.XXXXXX"); \
	trap 'rm -f "$$log"' EXIT HUP INT TERM; \
	if EXERCISE_IMPL=skeleton $(PYTHON_RUN) -m unittest discover -s $(TEST_DIR) -p 'test_stage_01_*.py' >"$$log" 2>&1; then \
		printf '%s\n' 'skeleton이 예상과 달리 1단계 검사를 통과했습니다.' >&2; \
		exit 1; \
	fi; \
	grep -Fq 'NotImplementedError' "$$log"; \
	printf '%s\n' 'skeleton의 첫 구현 경계를 확인했습니다.'

clean:
	@find docs exercises scripts -type d -name __pycache__ -prune -exec rm -rf -- {} +
	@find docs exercises scripts -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@rm -rf -- exercises/command-checker/workspace .guide
