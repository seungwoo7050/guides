SHELL := /bin/bash

.PHONY: prepare check verify clean

prepare:
	./prepare.sh

check:
	python3 scripts/validate.py
	python3 scripts/test_validate.py
	./scripts/smoke-javac.sh
	@while IFS= read -r -d '' script; do bash -n "$$script" || exit 1; done < <(find . -type f -name '*.sh' -not -path './.git/*' -not -path './.guide/*' -not -path './.workspace/*' -not -path '*/target/*' -print0)
	@echo "Java 가이드 빠른 검사 통과"

verify:
	./verify.sh

clean:
	rm -rf \
		target \
		examples/runtime-model/target \
		exercises/01-language-and-domain/01-first-program/reference/target \
		exercises/01-language-and-domain/01-first-program/skeleton/target \
		exercises/01-language-and-domain/02-value-object-contract/reference/target \
		exercises/01-language-and-domain/02-value-object-contract/skeleton/target \
		exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/target \
		exercises/02-runtime-and-concurrency/01-concurrent-state-update/skeleton/target \
		exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/target \
		exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/target \
		exercises/03-build-test-and-evidence/01-multi-repository-maven/.workspace \
		exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/target \
		exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/target \
		exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/target \
		exercises/03-build-test-and-evidence/02-state-and-effect-testing/skeleton/target \
		exercises/04-capstone/01-concurrent-job-ledger/reference/target \
		exercises/04-capstone/01-concurrent-job-ledger/skeleton/target
