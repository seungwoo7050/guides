CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -g
LDLIBS := -pthread
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
THREADFLAGS := -fsanitize=thread -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
TSAN_OPTIONS ?= halt_on_error=1
BUILD := build

.PHONY: all exercise-build exercise-test reference-test sanitize thread-sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/exercise: skeleton/src/account.c tests/test_account.c include/account.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) skeleton/src/account.c tests/test_account.c $(LDLIBS) -o $@

$(BUILD)/reference: reference/src/account.c tests/test_account.c include/account.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) reference/src/account.c tests/test_account.c $(LDLIBS) -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/account.c tests/test_account.c $(LDLIBS) $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference

thread-sanitize: clean | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREADFLAGS) reference/src/account.c tests/test_account.c $(LDLIBS) $(THREADFLAGS) -o $(BUILD)/reference-tsan
	TSAN_OPTIONS='$(TSAN_OPTIONS)' ./$(BUILD)/reference-tsan

clean:
	rm -rf $(BUILD)
