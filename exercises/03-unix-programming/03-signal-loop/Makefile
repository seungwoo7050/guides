CC ?= cc
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
EXERCISE_IMPL ?= workspace
EXERCISE_SOURCE := $(EXERCISE_IMPL)/signal_loop.c

.PHONY: all check-exercise-impl exercise-build exercise-test reference-test \
	exercise-sanitize reference-sanitize sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

check-exercise-impl:
	@case '$(EXERCISE_IMPL)' in workspace|skeleton) ;; \
		*) printf '%s\n' 'EXERCISE_IMPL은 workspace 또는 skeleton이어야 합니다.' >&2; exit 2 ;; \
	esac
	@test -f '$(EXERCISE_SOURCE)' || { \
		printf '%s\n' '먼저 저장소 루트에서 scripts/new-workspace.sh exercises/03-unix-programming/03-signal-loop를 실행하세요.' >&2; \
		exit 2; \
	}

$(BUILD)/exercise: check-exercise-impl | $(BUILD)
	$(CC) $(CFLAGS) '$(EXERCISE_SOURCE)' -o $@

$(BUILD)/reference: reference/signal_loop.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	python3 tests/check.py ./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	python3 tests/check.py ./$(BUILD)/reference

exercise-sanitize: clean check-exercise-impl | $(BUILD)
	$(CC) $(CFLAGS) $(SANFLAGS) '$(EXERCISE_SOURCE)' $(SANFLAGS) -o $(BUILD)/exercise
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		python3 tests/check.py ./$(BUILD)/exercise

reference-sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) $(SANFLAGS) reference/signal_loop.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		python3 tests/check.py ./$(BUILD)/reference

sanitize: exercise-sanitize

clean:
	rm -rf $(BUILD)
