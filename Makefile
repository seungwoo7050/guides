SHELL := /bin/bash

.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py
	python3 scripts/test_validate.py
	./scripts/smoke-javac.sh
	@while IFS= read -r -d '' script; do bash -n "$$script" || exit 1; done < <(find . -type f -name '*.sh' -not -path './.git/*' -not -path './.guide/*' -not -path '*/target/*' -print0)
	@echo "Java 가이드 빠른 검사 통과"

verify:
	./verify.sh

clean:
	rm -rf target
	find examples exercises -type d -name target -prune -exec rm -rf {} +
	find exercises -type d -name .workspace -prune -exec rm -rf {} +
