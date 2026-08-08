SHELL := /bin/bash

.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py
	python3 scripts/test-validator.py
	@while IFS= read -r script; do bash -n "$$script"; done < <(find . -type f -name '*.sh' -not -path '*/target/*' -not -path './.guide/*' -not -path './.workspace/*' | sort)
	@printf '[PASS] 빠른 구조 검사\n'

verify:
	./verify.sh

clean:
	rm -rf target
	find exercises -type d \( -path '*/reference/target' -o -path '*/skeleton/target' -o -path 'exercises/test-support/target' \) -prune -exec rm -rf {} +
	find scripts exercises -type d -name __pycache__ -prune -exec rm -rf {} +
	find scripts exercises -type f -name '*.pyc' -delete
