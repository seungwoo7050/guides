.PHONY: prepare check verify fixtures example clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify.py --quick

verify:
	./verify.sh

fixtures:
	python3 scripts/verify.py --fixtures-only

example:
	python3 examples/fixed-step-replay/sim.py --verify --pretty

clean:
	rm -rf .guide
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
