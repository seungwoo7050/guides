.PHONY: prepare check verify negative-check clean

prepare:
	@./prepare.sh

check:
	@python3 scripts/validate.py
	@python3 scripts/test-validator.py
	@./scripts/test-prepare-safety.sh
	@python3 scripts/test_answer_mutants.py
	@./exercises/system-investigation/check.sh all
	@python3 scripts/test_lab_cli.py

verify:
	@./verify.sh

negative-check:
	@./scripts/test-verify-negatives.sh

clean:
	@printf '%s\n' 'workspace와 .guide는 사용자·준비 상태이므로 자동 삭제하지 않습니다.'
