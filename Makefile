SHELL := /bin/sh

ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
TSAN_OPTIONS ?= halt_on_error=1
READLINE_CPPFLAGS ?=
READLINE_LDFLAGS ?=
READLINE_LDLIBS ?= -lreadline

export ASAN_OPTIONS ASAN_PROCESS_OPTIONS UBSAN_OPTIONS TSAN_OPTIONS
export READLINE_CPPFLAGS READLINE_LDFLAGS READLINE_LDLIBS

EXAMPLES := \
	examples/fd-redirection \
	examples/process-group-forwarding \
	examples/readline-repl \
	examples/text-checks

SANITIZE_EXAMPLES := \
	examples/fd-redirection \
	examples/process-group-forwarding \
	examples/readline-repl

.PHONY: all check structure-check validator-check docs-check workspace-check \
	examples-check exercises-check exercise-test quality-check sanitize \
	thread-sanitize readline-check clean

all: check

check: validator-check docs-check workspace-check examples-check exercises-check

structure-check:
	python3 scripts/validate_repository.py

validator-check: structure-check
	python3 scripts/test-validator.py

docs-check:
	python3 scripts/validate_docs.py

workspace-check:
	python3 scripts/test_workspace.py

examples-check:
	@set -eu; \
	for dir in $(EXAMPLES); do \
		printf '\n==> %s\n' "$$dir"; \
		$(MAKE) -C "$$dir" check; \
	done

exercises-check:
	$(MAKE) -C exercises check

exercise-test:
	$(MAKE) -C exercises exercise-test

quality-check: validator-check docs-check workspace-check
	$(MAKE) -C exercises quality-check

sanitize:
	@set -eu; \
	for dir in $(SANITIZE_EXAMPLES); do \
		printf '\n==> %s (sanitize)\n' "$$dir"; \
		case "$$dir" in \
			examples/process-group-forwarding) \
				ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' $(MAKE) -C "$$dir" sanitize ;; \
			*) \
				$(MAKE) -C "$$dir" sanitize ;; \
		esac; \
	done
	$(MAKE) -C exercises reference-sanitize

thread-sanitize:
	$(MAKE) -C exercises reference-thread-sanitize

readline-check:
	$(MAKE) -C examples/readline-repl readline-check

clean:
	@failed=0; \
	for dir in $(EXAMPLES); do \
		if ! $(MAKE) -C "$$dir" clean >/dev/null 2>&1; then \
			printf '정리 실패: %s\n' "$$dir" >&2; \
			failed=1; \
		fi; \
	done; \
	if ! $(MAKE) -C exercises clean >/dev/null 2>&1; then \
		printf '정리 실패: exercises\n' >&2; \
		failed=1; \
	fi; \
	find examples exercises -type d -name '*.dSYM' -prune -exec rm -rf {} +; \
	find examples exercises -type d -name '__pycache__' -prune -exec rm -rf {} +; \
	find examples exercises -type f \( -name '*.pyc' -o -name 'core' -o -name 'core.*' \) -delete; \
	rm -f a.out core core.* verify.log; \
	exit $$failed
