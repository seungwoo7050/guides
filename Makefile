.PHONY: prepare check verify quality-check examples fixtures contracts workspace submission clean

prepare:
	./prepare.sh

check: examples fixtures contracts
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

workspace:
	./scripts/new-workspace.sh

submission:
	python3 scripts/check-submission.py --workspace exercises/model-lifecycle/workspace --stage 8

clean:
	python3 scripts/clean.py
