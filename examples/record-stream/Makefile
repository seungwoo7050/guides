CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
LDFLAGS ?=

BUILD := build
TEST := $(BUILD)/test_line_reader
OBJS := $(BUILD)/line_reader.o $(BUILD)/test_line_reader.o
DEPS := $(OBJS:.o=.d)

.PHONY: all check clean sanitize
all: $(TEST)

$(TEST): $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

$(BUILD)/line_reader.o: src/line_reader.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILD)/test_line_reader.o: tests/test_line_reader.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

check: $(TEST)
	./$(TEST)

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
	        LDFLAGS='$(LDFLAGS) -fsanitize=address,undefined' check

clean:
	rm -rf -- build

-include $(DEPS)
