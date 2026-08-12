CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
EXERCISE_IMPL ?= workspace
EXERCISE_SOURCE := $(EXERCISE_IMPL)/src/command_pipeline.c
HELPERS := \
	$(BUILD)/emit-bytes \
	$(BUILD)/expect-bytes \
	$(BUILD)/exit-with \
	$(BUILD)/terminate-with

.PHONY: all check-exercise-impl exercise-build exercise-test reference-test \
	exercise-sanitize reference-sanitize sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/emit-bytes: tests/helpers/emit_bytes.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/expect-bytes: tests/helpers/expect_bytes.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/exit-with: tests/helpers/exit_with.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/terminate-with: tests/helpers/terminate_with.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

check-exercise-impl:
	@case '$(EXERCISE_IMPL)' in workspace|skeleton) ;; \
		*) printf '%s\n' 'EXERCISE_IMPL은 workspace 또는 skeleton이어야 합니다.' >&2; exit 2 ;; \
	esac
	@test -f '$(EXERCISE_SOURCE)' || { \
		printf '%s\n' '먼저 저장소 루트에서 scripts/new-workspace.sh exercises/03-unix-programming/02-command-pipeline를 실행하세요.' >&2; \
		exit 2; \
	}

$(BUILD)/exercise: check-exercise-impl tests/test_command_pipeline.c include/command_pipeline.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) '$(EXERCISE_SOURCE)' tests/test_command_pipeline.c -o $@

$(BUILD)/reference: reference/src/command_pipeline.c tests/test_command_pipeline.c include/command_pipeline.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/command_pipeline.c tests/test_command_pipeline.c -o $@

exercise-build: $(BUILD)/exercise $(HELPERS)

exercise-test: exercise-build
	./$(BUILD)/exercise ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

reference-test: $(BUILD)/reference $(HELPERS)
	./$(BUILD)/reference ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

exercise-sanitize: clean check-exercise-impl | $(BUILD)
	$(CC) $(CFLAGS) tests/helpers/emit_bytes.c -o $(BUILD)/emit-bytes
	$(CC) $(CFLAGS) tests/helpers/expect_bytes.c -o $(BUILD)/expect-bytes
	$(CC) $(CFLAGS) tests/helpers/exit_with.c -o $(BUILD)/exit-with
	$(CC) $(CFLAGS) tests/helpers/terminate_with.c -o $(BUILD)/terminate-with
	$(CC) $(CPPFLAGS) $(CFLAGS) -DTEST_TIMEOUT_SECONDS=120 $(SANFLAGS) '$(EXERCISE_SOURCE)' tests/test_command_pipeline.c $(SANFLAGS) -o $(BUILD)/exercise
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/exercise ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

reference-sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) tests/helpers/emit_bytes.c -o $(BUILD)/emit-bytes
	$(CC) $(CFLAGS) tests/helpers/expect_bytes.c -o $(BUILD)/expect-bytes
	$(CC) $(CFLAGS) tests/helpers/exit_with.c -o $(BUILD)/exit-with
	$(CC) $(CFLAGS) tests/helpers/terminate_with.c -o $(BUILD)/terminate-with
	$(CC) $(CPPFLAGS) $(CFLAGS) -DTEST_TIMEOUT_SECONDS=120 $(SANFLAGS) reference/src/command_pipeline.c tests/test_command_pipeline.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

sanitize: exercise-sanitize

clean:
	rm -rf $(BUILD)
