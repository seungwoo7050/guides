.PHONY: prepare check verify exercise clean

prepare:
	./prepare.sh

check:
	python3 scripts/verify_repository.py --quick

verify:
	./verify.sh

exercise:
	@test -n "$(NAME)" || (echo '사용법: make exercise NAME=01-platform-product FILE=.workspace/.../submission.json' >&2; exit 2)
	@test -n "$(FILE)" || (echo 'FILE을 지정하십시오.' >&2; exit 2)
	python3 scripts/verify_submission.py exercises/$(NAME)/contract.json $(FILE)

clean:
	rm -rf .guide
	find scripts -type d -name __pycache__ -prune -exec rm -rf {} +
