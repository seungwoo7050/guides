SHELL := /bin/sh

EXERCISES := \
	01-foundations/01-number-report \
	02-c-language/01-textkit \
	02-c-language/02-owned-string \
	02-c-language/03-int-vector \
	02-c-language/04-diagnostic-formatter \
	03-unix-programming/01-record-stream \
	03-unix-programming/02-command-pipeline \
	03-unix-programming/03-signal-loop \
	03-unix-programming/04-command-runner \
	04-concurrency/01-account-simulator

.PHONY: all check reference-test exercise-build exercise-test quality-check \
	sanitize reference-sanitize thread-sanitize reference-thread-sanitize clean

all: check

check: reference-test

reference-test:
	@set -eu; \
	for dir in $(EXERCISES); do \
		printf '\n==> exercises/%s (reference-test)\n' "$$dir"; \
		$(MAKE) -C "$$dir" reference-test; \
	done

exercise-build:
	@set -eu; \
	for dir in $(EXERCISES); do \
		printf '\n==> exercises/%s (exercise-build)\n' "$$dir"; \
		$(MAKE) -C "$$dir" exercise-build; \
	done

exercise-test:
	@set -eu; \
	for dir in $(EXERCISES); do \
		printf '\n==> exercises/%s (exercise-test)\n' "$$dir"; \
		$(MAKE) -C "$$dir" exercise-test; \
	done

quality-check: reference-test
	@set -eu; \
	output=$$(mktemp "$${TMPDIR:-/tmp}/guide-c-skeleton.XXXXXX"); \
	trap 'rm -f "$$output"' EXIT HUP INT TERM; \
	for dir in $(EXERCISES); do \
		printf '\n==> exercises/%s (skeleton 빌드)\n' "$$dir"; \
		$(MAKE) --no-print-directory -C "$$dir" clean >/dev/null; \
		$(MAKE) --no-print-directory -C "$$dir" exercise-build EXERCISE_IMPL=skeleton; \
		printf '==> exercises/%s (초기 동작 실패 확인)\n' "$$dir"; \
		if $(MAKE) --no-print-directory -C "$$dir" exercise-test EXERCISE_IMPL=skeleton >"$$output" 2>&1; then \
			cat "$$output"; \
			printf '오류: 초기 skeleton이 동작 테스트를 통과했습니다: %s\n' "$$dir" >&2; \
			exit 1; \
		fi; \
		$(MAKE) --no-print-directory -C "$$dir" clean >/dev/null; \
	done; \
	printf '\nskeleton 계약 통과: 기준 구현 통과, skeleton 빌드 성공·동작 실패: %s개\n' "$(words $(EXERCISES))"

reference-sanitize:
	@set -eu; \
	for dir in $(EXERCISES); do \
		printf '\n==> exercises/%s (reference-sanitize)\n' "$$dir"; \
		$(MAKE) -C "$$dir" reference-sanitize; \
	done

sanitize: reference-sanitize

reference-thread-sanitize:
	$(MAKE) -C 04-concurrency/01-account-simulator reference-thread-sanitize

thread-sanitize: reference-thread-sanitize

clean:
	@failed=0; \
	for dir in $(EXERCISES); do \
		if ! $(MAKE) -C "$$dir" clean >/dev/null 2>&1; then \
			printf '정리 실패: exercises/%s\n' "$$dir" >&2; \
			failed=1; \
		fi; \
	done; \
	exit $$failed
