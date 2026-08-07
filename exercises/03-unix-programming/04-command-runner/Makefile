CC ?= cc
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
HELPERS := \
	$(BUILD)/print-args \
	$(BUILD)/emit-bytes \
	$(BUILD)/expect-bytes \
	$(BUILD)/exit-with \
	$(BUILD)/terminate-with \
	$(BUILD)/mark-file

.PHONY: all exercise-build exercise-test reference-test sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/print-args: tests/helpers/print_args.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/emit-bytes: tests/helpers/emit_bytes.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/expect-bytes: tests/helpers/expect_bytes.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/exit-with: tests/helpers/exit_with.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/terminate-with: tests/helpers/terminate_with.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/mark-file: tests/helpers/mark_file.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/exercise: skeleton/command_runner.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/reference: reference/command_runner.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

exercise-build: $(BUILD)/exercise $(HELPERS)

exercise-test: exercise-build
	python3 tests/check.py ./$(BUILD)/exercise ./$(BUILD)/print-args ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with ./$(BUILD)/mark-file

reference-test: $(BUILD)/reference $(HELPERS)
	python3 tests/check.py ./$(BUILD)/reference ./$(BUILD)/print-args ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with ./$(BUILD)/mark-file

sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) tests/helpers/print_args.c -o $(BUILD)/print-args
	$(CC) $(CFLAGS) tests/helpers/emit_bytes.c -o $(BUILD)/emit-bytes
	$(CC) $(CFLAGS) tests/helpers/expect_bytes.c -o $(BUILD)/expect-bytes
	$(CC) $(CFLAGS) tests/helpers/exit_with.c -o $(BUILD)/exit-with
	$(CC) $(CFLAGS) tests/helpers/terminate_with.c -o $(BUILD)/terminate-with
	$(CC) $(CFLAGS) tests/helpers/mark_file.c -o $(BUILD)/mark-file
	$(CC) $(CFLAGS) $(SANFLAGS) reference/command_runner.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		python3 tests/check.py ./$(BUILD)/reference ./$(BUILD)/print-args ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with ./$(BUILD)/mark-file

clean:
	rm -rf $(BUILD)
