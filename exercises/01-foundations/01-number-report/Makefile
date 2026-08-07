CC ?= cc
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -Werror -g
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS ?= halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS ?= halt_on_error=1:print_stacktrace=1
BUILD := build

.PHONY: all exercise-build exercise-test reference-test sanitize clean

all: reference-test

$(BUILD):
	mkdir -p $@

$(BUILD)/exercise: skeleton/number_report.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD)/reference: reference/number_report.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

exercise-build: $(BUILD)/exercise

exercise-test: exercise-build
	./tests/check.sh ./$(BUILD)/exercise

reference-test: $(BUILD)/reference
	./tests/check.sh ./$(BUILD)/reference

sanitize: clean | $(BUILD)
	$(CC) $(CFLAGS) $(SANFLAGS) reference/number_report.c $(SANFLAGS) -o $(BUILD)/reference
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' \
		./tests/check.sh ./$(BUILD)/reference

clean:
	rm -rf $(BUILD)
