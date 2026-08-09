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
	rm -rf .guide
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
