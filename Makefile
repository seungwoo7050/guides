.PHONY: prepare check verify test-infrastructure clean

prepare:
	./prepare.sh

check:
	./verify.sh

verify:
	./verify.sh

test-infrastructure:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v

clean:
	python3 "$(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts/clean_generated.py"
