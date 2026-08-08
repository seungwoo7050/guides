SHELL := /bin/bash

.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py
	@while IFS= read -r script; do bash -n "$$script"; done < <(find . -type f -name '*.sh' -not -path '*/target/*' -not -path './.guide/*' | sort)
	@printf '[PASS] 빠른 구조 검사\n'

verify:
	./verify.sh

clean:
	rm -rf .guide/tmp .guide/verify
	find . -type d -name target -prune -exec rm -rf {} +
	@if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then \
	  ./exercises/90-optional-labs/single-broker-kraft/verify.sh --cleanup >/dev/null 2>&1 || true; \
	fi
