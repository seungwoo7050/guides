CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L

.PHONY: all check clean sanitize
all: command_pipeline

command_pipeline: src/command_pipeline.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: command_pipeline
	./tests/check.sh

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' check

clean:
	rm -f command_pipeline
