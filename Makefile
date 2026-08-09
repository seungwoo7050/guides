.PHONY: prepare check verify workspace clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify.py --quick

verify:
	./verify.sh

workspace:
	./scripts/new-capstone-workspace.sh

clean:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/clean_generated.py
