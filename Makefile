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
	@rm -rf -- \
		target \
		scripts/__pycache__ \
		exercises/application-boundaries/reference/target \
		exercises/application-boundaries/skeleton/target \
		exercises/security-boundaries/reference/target \
		exercises/security-boundaries/skeleton/target \
		exercises/transaction-locking/reference/target \
		exercises/transaction-locking/skeleton/target \
		exercises/idempotency-outbox/reference/target \
		exercises/idempotency-outbox/skeleton/target \
		exercises/kafka-avro-contract/reference/target \
		exercises/kafka-avro-contract/skeleton/target \
		exercises/resilient-http-client/reference/target \
		exercises/resilient-http-client/skeleton/target \
		exercises/single-service-capstone/reference/target \
		exercises/single-service-capstone/skeleton/target
