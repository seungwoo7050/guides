CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build
HELPERS := \
	$(BUILD)/emit-bytes \
	$(BUILD)/expect-bytes \
	$(BUILD)/exit-with \
	$(BUILD)/terminate-with

.PHONY: all exercise-build exercise-test reference-test sanitize clean

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

$(BUILD)/exercise: skeleton/src/command_pipeline.c tests/test_command_pipeline.c include/command_pipeline.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) skeleton/src/command_pipeline.c tests/test_command_pipeline.c -o $@

$(BUILD)/reference: reference/src/command_pipeline.c tests/test_command_pipeline.c include/command_pipeline.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/command_pipeline.c tests/test_command_pipeline.c -o $@

exercise-build: $(BUILD)/exercise $(HELPERS)

exercise-test: exercise-build
	./$(BUILD)/exercise ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

reference-test: $(BUILD)/reference $(HELPERS)
	./$(BUILD)/reference ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) tests/helpers/emit_bytes.c -o $(BUILD)/emit-bytes
	$(CC) $(CFLAGS) tests/helpers/expect_bytes.c -o $(BUILD)/expect-bytes
	$(CC) $(CFLAGS) tests/helpers/exit_with.c -o $(BUILD)/exit-with
	$(CC) $(CFLAGS) tests/helpers/terminate_with.c -o $(BUILD)/terminate-with
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/command_pipeline.c tests/test_command_pipeline.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_PROCESS_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference ./$(BUILD)/emit-bytes ./$(BUILD)/expect-bytes ./$(BUILD)/exit-with ./$(BUILD)/terminate-with

clean:
	rm -rf $(BUILD)
