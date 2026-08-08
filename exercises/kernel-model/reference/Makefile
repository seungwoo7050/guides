SHELL := /bin/sh
PYTHON ?= python3

.PHONY: check bytecode clean

check:
	$(PYTHON) ../check.py reference

bytecode:
	$(PYTHON) -m compileall -q .

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
