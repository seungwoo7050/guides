PYTHON ?= python3

.PHONY: prepare check verify clean list-exercises validate examples-check exercise-check verification-tests

prepare:
	./prepare.sh

check: validate examples-check exercise-check verification-tests

validate:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/validate.py --quick

examples-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m unittest discover -s tests -p 'test_*.py'

exercise-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/exercise_tool.py verify-all

verification-tests:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/test_repository_state.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/test_validator.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/test_prepare_safety.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/test_verify_preflight.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/test_clean_safety.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/test_workspace_tools.py

verify:
	./verify.sh

clean:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/clean_generated.py

list-exercises:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/exercise_tool.py list
