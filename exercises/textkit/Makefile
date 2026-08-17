CC ?= cc
CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=
AR ?= ar
ARFLAGS ?= rcs

BUILD_DIR := build
LIB := $(BUILD_DIR)/libtextkit.a
CLI := $(BUILD_DIR)/textstat
LIB_OBJ := $(BUILD_DIR)/textkit.o
TEST_BIN := $(BUILD_DIR)/test-textkit

.PHONY: all test sanitize clean fclean re

all: $(LIB) $(CLI)

$(BUILD_DIR):
	mkdir -p $@

$(LIB_OBJ): src/textkit.c include/textkit.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(LIB): $(LIB_OBJ)
	$(AR) $(ARFLAGS) $@ $^

$(CLI): app/main.c $(LIB) include/textkit.h
	$(CC) $(CPPFLAGS) $(CFLAGS) app/main.c $(LIB) $(LDFLAGS) -o $@

$(TEST_BIN): tests/test_textkit.c $(LIB) include/textkit.h
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_textkit.c $(LIB) $(LDFLAGS) -o $@

test: $(CLI) $(TEST_BIN)
	./$(TEST_BIN)
	./tests/check_cli.sh ./$(CLI)

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test

clean:
	rm -rf $(BUILD_DIR)

fclean: clean

re: fclean all
