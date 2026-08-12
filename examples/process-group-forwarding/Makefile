CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L

.PHONY: all check sanitize clean

all: process_group_forwarding

process_group_forwarding: src/process_group_forwarding.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: process_group_forwarding
	./tests/check.sh

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' check

clean:
	rm -f process_group_forwarding
