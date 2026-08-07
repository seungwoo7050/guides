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

$(BUILD)/exercise: skeleton/src/owned_string.c tests/test_owned_string.c include/owned_string.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) skeleton/src/owned_string.c tests/test_owned_string.c -o $@

$(BUILD)/reference: reference/src/owned_string.c tests/test_owned_string.c include/owned_string.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/owned_string.c tests/test_owned_string.c -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/owned_string.c tests/test_owned_string.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference

clean:
	rm -rf $(BUILD)
