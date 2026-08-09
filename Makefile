.PHONY: prepare check verify quality-check examples fixtures contracts lifecycle-reference modern-reference workspace submission clean

prepare:
	./prepare.sh

check: examples fixtures contracts lifecycle-reference modern-reference
	python3 scripts/verify-docs.py

verify:
	./verify.sh

quality-check:
	python3 scripts/quality-check.py

examples:
	python3 -m unittest discover -s tests -p 'test_*.py'

fixtures:
	python3 scripts/verify-fixtures.py

contracts:
	python3 scripts/verify-contracts.py

lifecycle-reference:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=exercises/model-lifecycle/reference/src python3 -m unittest discover -s exercises/model-lifecycle/reference/tests -p 'test_*.py'
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/check-submission.py --workspace exercises/model-lifecycle/reference --stage 8

modern-reference:
	PYTHONDONTWRITEBYTECODE=1 python3 exercises/modern-model-release/tests/check.py --candidate exercises/modern-model-release/reference

workspace:
	./scripts/new-workspace.sh

submission:
	python3 scripts/check-submission.py --workspace exercises/model-lifecycle/workspace --stage 8

clean:
	python3 scripts/clean.py
