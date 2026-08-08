SHELL := /bin/bash

.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py
	python3 scripts/test-validator.py
	@while IFS= read -r script; do bash -n "$$script"; done < <(find . -type f -name '*.sh' -not -path '*/target/*' -not -path './.guide/*' | sort)
	@printf '[PASS] 빠른 구조 검사\n'

verify:
	./verify.sh

clean:
	find . -type d -name target -prune -exec rm -rf {} +
	find . -type d -name __pycache__ -not -path './.guide/*' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -not -path './.guide/*' -delete
