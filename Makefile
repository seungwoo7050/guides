SHELL := /bin/sh

.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py
	python3 scripts/validator_self_test.py
	@bash -n prepare.sh verify.sh
	@find scripts -type f -name '*.sh' -exec bash -n {} \;
	./scripts/mvn-guide.sh -DskipTests compile
	@printf 'Spring Boot 가이드 정적 검사를 통과했습니다.\n'

verify:
	./verify.sh

clean:
	@find . -path './.git' -prune -o -path './.guide' -prune -o -type d -name target -prune -exec rm -rf -- {} +
	@find . -path './.git' -prune -o -path './.guide' -prune -o -type d -name __pycache__ -prune -exec rm -rf -- {} +
	@find . -path './.git' -prune -o -path './.guide' -prune -o -type f -name '*.pyc' -delete
