CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L

.PHONY: all check sanitize clean

all: fd_redirection

fd_redirection: src/fd_redirection.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: fd_redirection
	./tests/check.sh

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' check

clean:
	rm -f fd_redirection
