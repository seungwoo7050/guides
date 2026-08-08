.PHONY: prepare check verify negative-check clean

prepare:
	@./prepare.sh

check:
	@python3 scripts/validate.py
	@python3 scripts/test-validator.py
	@./scripts/test-prepare-safety.sh
	@./scripts/validate.sh

verify:
	@./verify.sh

negative-check:
	@./scripts/test-verify-negatives.sh

clean:
	@printf '%s\n' '생성 실습 workspace와 .guide는 사용자 상태이므로 자동 삭제하지 않습니다.'
