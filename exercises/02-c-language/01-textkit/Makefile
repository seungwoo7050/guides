CC ?= cc
AR ?= ar
CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build

.PHONY: all exercise-build exercise-test reference-test sanitize clean

all: reference-test

$(BUILD)/exercise $(BUILD)/reference:
	mkdir -p $@

$(BUILD)/exercise/textkit.o: skeleton/src/textkit.c include/textkit.h | $(BUILD)/exercise
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

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

sanitize: clean | $(BUILD)/reference
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) reference/src/textkit.c tests/test_textkit.c $(SANFLAGS) -o $(BUILD)/reference/test
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./$(BUILD)/reference/test

clean:
	rm -rf $(BUILD)
