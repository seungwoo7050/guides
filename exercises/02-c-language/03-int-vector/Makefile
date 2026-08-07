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

$(BUILD)/exercise: skeleton/src/int_vector.c tests/test_int_vector.c include/int_vector.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) skeleton/src/int_vector.c tests/test_int_vector.c -o $@

$(BUILD)/reference: reference/src/int_vector.c tests/test_int_vector.c include/int_vector.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/int_vector.c tests/test_int_vector.c -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/int_vector.c tests/test_int_vector.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference

clean:
	rm -rf $(BUILD)
