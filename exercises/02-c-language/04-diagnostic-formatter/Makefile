CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build

.PHONY: all exercise-build exercise-test reference-test sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/exercise: skeleton/src/diagnostic_formatter.c tests/test_diagnostic_formatter.c include/diagnostic_formatter.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) skeleton/src/diagnostic_formatter.c tests/test_diagnostic_formatter.c -o $@

$(BUILD)/reference: reference/src/diagnostic_formatter.c tests/test_diagnostic_formatter.c include/diagnostic_formatter.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/diagnostic_formatter.c tests/test_diagnostic_formatter.c -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/diagnostic_formatter.c tests/test_diagnostic_formatter.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference

clean:
	rm -rf $(BUILD)
