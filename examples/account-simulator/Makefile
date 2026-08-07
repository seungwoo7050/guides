CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror -pthread
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
LDFLAGS ?= -pthread

.PHONY: all check clean sanitize thread-check
all: account_simulator

account_simulator: src/account_simulator.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

check: account_simulator
	./tests/check.sh

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
	        LDFLAGS='$(LDFLAGS) -fsanitize=address,undefined' check

thread-check: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=thread -fno-omit-frame-pointer' \
	        LDFLAGS='$(LDFLAGS) -fsanitize=thread' check

clean:
	rm -f account_simulator
