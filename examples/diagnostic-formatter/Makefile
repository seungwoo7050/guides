CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude
LDFLAGS ?=

BUILD := build
TEST := $(BUILD)/test_mini_format
OBJS := $(BUILD)/mini_format.o $(BUILD)/test_mini_format.o
DEPS := $(OBJS:.o=.d)

.PHONY: all check clean sanitize
all: $(TEST)

$(TEST): $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

$(BUILD)/mini_format.o: src/mini_format.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILD)/test_mini_format.o: tests/test_mini_format.c
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
