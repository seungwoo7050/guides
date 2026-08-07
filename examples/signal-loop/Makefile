CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L

.PHONY: all check clean sanitize
all: signal_loop

signal_loop: src/signal_loop.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: signal_loop
	./tests/check.sh

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' check

clean:
	rm -f signal_loop
