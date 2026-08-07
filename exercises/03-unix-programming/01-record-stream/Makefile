CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build

.PHONY: all exercise-build exercise-test reference-test sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/exercise: skeleton/src/record_stream.c tests/test_record_stream.c include/record_stream.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) skeleton/src/record_stream.c tests/test_record_stream.c -o $@

$(BUILD)/reference: reference/src/record_stream.c tests/test_record_stream.c include/record_stream.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/record_stream.c tests/test_record_stream.c -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/record_stream.c tests/test_record_stream.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference

clean:
	rm -rf $(BUILD)
