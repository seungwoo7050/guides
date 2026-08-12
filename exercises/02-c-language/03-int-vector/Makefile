CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
EXERCISE_IMPL ?= workspace
EXERCISE_SOURCE := $(EXERCISE_IMPL)/src/int_vector.c

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
		printf '%s\n' '먼저 저장소 루트에서 scripts/new-workspace.sh exercises/02-c-language/03-int-vector를 실행하세요.' >&2; \
		exit 2; \
	}

$(BUILD)/exercise: check-exercise-impl tests/test_int_vector.c include/int_vector.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) '$(EXERCISE_SOURCE)' tests/test_int_vector.c -o $@

$(BUILD)/reference: reference/src/int_vector.c tests/test_int_vector.c include/int_vector.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/int_vector.c tests/test_int_vector.c -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./$(BUILD)/reference

exercise-sanitize: clean check-exercise-impl | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) '$(EXERCISE_SOURCE)' tests/test_int_vector.c $(SANFLAGS) -o $(BUILD)/exercise
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/exercise

reference-sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/int_vector.c tests/test_int_vector.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference

sanitize: exercise-sanitize

clean:
	rm -rf $(BUILD)
