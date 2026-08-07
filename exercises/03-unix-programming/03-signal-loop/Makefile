CC ?= cc
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build

.PHONY: all exercise-build exercise-test reference-test sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/exercise: skeleton/signal_loop.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/reference: reference/signal_loop.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	python3 tests/check.py ./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	python3 tests/check.py ./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) $(SANFLAGS) reference/signal_loop.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		python3 tests/check.py ./$(BUILD)/reference

clean:
	rm -rf $(BUILD)
