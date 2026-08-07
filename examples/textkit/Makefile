CC ?= cc
AR ?= ar
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude
LDFLAGS ?=
LDLIBS ?=

BUILD := build
LIB := libtextkit.a
APP := textstat
TEST := $(BUILD)/test_textkit
LIB_OBJ := $(BUILD)/textkit.o
APP_OBJ := $(BUILD)/main.o
TEST_OBJ := $(BUILD)/test_textkit.o
DEPS := $(LIB_OBJ:.o=.d) $(APP_OBJ:.o=.d) $(TEST_OBJ:.o=.d)

.PHONY: all check clean sanitize

all: $(APP)

$(LIB): $(LIB_OBJ)
	rm -f $@
	$(AR) rcs $@ $^

$(APP): $(APP_OBJ) $(LIB)
	$(CC) $(LDFLAGS) $(APP_OBJ) $(LIB) $(LDLIBS) -o $@

$(TEST): $(TEST_OBJ) $(LIB)
	$(CC) $(LDFLAGS) $(TEST_OBJ) $(LIB) $(LDLIBS) -o $@

$(BUILD)/%.o: src/%.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILD)/test_textkit.o: tests/test_textkit.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

check: $(APP) $(TEST)
	./$(TEST)
	./tests/smoke.sh

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
	        LDFLAGS='$(LDFLAGS) -fsanitize=address,undefined' check

clean:
	rm -rf -- build
	rm -f -- libtextkit.a textstat

-include $(DEPS)
