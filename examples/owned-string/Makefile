CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude
LDFLAGS ?=

BUILD := build
TEST := $(BUILD)/test_owned_string
FAILURE_TEST := $(BUILD)/test_allocation_failure
OBJS := $(BUILD)/owned_string.o $(BUILD)/test_owned_string.o
DEPS := $(OBJS:.o=.d)

.PHONY: all check clean sanitize
all: $(TEST)

$(TEST): $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

$(BUILD)/owned_string.o: src/owned_string.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILD)/test_owned_string.o: tests/test_owned_string.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

check: $(TEST) $(FAILURE_TEST)
	./$(TEST)
	./$(FAILURE_TEST)

$(FAILURE_TEST): tests/test_allocation_failure.c src/owned_string.c include/owned_string.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
	        LDFLAGS='$(LDFLAGS) -fsanitize=address,undefined' check

clean:
	rm -rf -- build

-include $(DEPS)
