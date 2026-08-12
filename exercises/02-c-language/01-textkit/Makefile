CC ?= cc
AR ?= ar
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
EXERCISE_IMPL ?= workspace
EXERCISE_SOURCE := $(EXERCISE_IMPL)/src/textkit.c

.PHONY: all check-exercise-impl exercise-build exercise-test reference-test \
	exercise-sanitize reference-sanitize sanitize clean

all: reference-test

$(BUILD)/exercise $(BUILD)/reference:
	mkdir -p $@

check-exercise-impl:
	@case '$(EXERCISE_IMPL)' in workspace|skeleton) ;; \
		*) printf '%s\n' 'EXERCISE_IMPL은 workspace 또는 skeleton이어야 합니다.' >&2; exit 2 ;; \
	esac
	@test -f '$(EXERCISE_SOURCE)' || { \
		printf '%s\n' '먼저 저장소 루트에서 scripts/new-workspace.sh exercises/02-c-language/01-textkit를 실행하세요.' >&2; \
		exit 2; \
	}

$(BUILD)/exercise/textkit.o: check-exercise-impl include/textkit.h | $(BUILD)/exercise
	$(CC) $(CPPFLAGS) $(CFLAGS) -c '$(EXERCISE_SOURCE)' -o $@

$(BUILD)/reference/textkit.o: reference/src/textkit.c include/textkit.h | $(BUILD)/reference
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD)/exercise/libtextkit.a: $(BUILD)/exercise/textkit.o
	$(AR) rcs $@ $^

$(BUILD)/reference/libtextkit.a: $(BUILD)/reference/textkit.o
	$(AR) rcs $@ $^

$(BUILD)/exercise/test: tests/test_textkit.c $(BUILD)/exercise/libtextkit.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/exercise/libtextkit.a -o $@

$(BUILD)/reference/test: tests/test_textkit.c $(BUILD)/reference/libtextkit.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/reference/libtextkit.a -o $@

$(BUILD)/exercise/textstat: app/main.c $(BUILD)/exercise/libtextkit.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/exercise/libtextkit.a -o $@

$(BUILD)/reference/textstat: app/main.c $(BUILD)/reference/libtextkit.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/reference/libtextkit.a -o $@

exercise-build: $(BUILD)/exercise/test $(BUILD)/exercise/textstat

exercise-test: exercise-build
	./$(BUILD)/exercise/test
	./tests/check_cli.sh ./$(BUILD)/exercise/textstat

reference-test: $(BUILD)/reference/test $(BUILD)/reference/textstat
	./$(BUILD)/reference/test
	./tests/check_cli.sh ./$(BUILD)/reference/textstat

exercise-sanitize: clean check-exercise-impl | $(BUILD)/exercise
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) '$(EXERCISE_SOURCE)' tests/test_textkit.c $(SANFLAGS) -o $(BUILD)/exercise/test
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/exercise/test

reference-sanitize: clean | $(BUILD)/reference
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/textkit.c tests/test_textkit.c $(SANFLAGS) -o $(BUILD)/reference/test
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference/test

sanitize: exercise-sanitize

clean:
	rm -rf $(BUILD)
