CC ?= cc
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
EXERCISE_IMPL ?= workspace
EXERCISE_SOURCE := $(EXERCISE_IMPL)/number_report.c

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
		printf '%s\n' '먼저 저장소 루트에서 scripts/new-workspace.sh exercises/01-foundations/01-number-report를 실행하세요.' >&2; \
		exit 2; \
	}

$(BUILD)/exercise: check-exercise-impl | $(BUILD)
	$(CC) $(CFLAGS) '$(EXERCISE_SOURCE)' -o $@

$(BUILD)/reference: reference/number_report.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./tests/check.sh ./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./tests/check.sh ./$(BUILD)/reference

exercise-sanitize: clean check-exercise-impl | $(BUILD)
	$(CC) $(CFLAGS) $(SANFLAGS) '$(EXERCISE_SOURCE)' $(SANFLAGS) -o $(BUILD)/exercise
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./tests/check.sh ./$(BUILD)/exercise

reference-sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) $(SANFLAGS) reference/number_report.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./tests/check.sh ./$(BUILD)/reference

sanitize: exercise-sanitize

clean:
	rm -rf $(BUILD)
