CC ?= cc
CPPFLAGS ?=
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=

NAME := number-report
BUILD_DIR := build
BIN := $(BUILD_DIR)/$(NAME)
SRC := src/number_report.c

.PHONY: all test sanitize clean fclean re

all: $(BIN)

$(BIN): $(SRC)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SRC) $(LDFLAGS) -o $@

test: $(BIN)
	./tests/check.sh ./$(BIN)

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test

clean:
	rm -rf $(BUILD_DIR)

fclean: clean

re: fclean all
