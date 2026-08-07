CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
LDFLAGS ?=
LDLIBS ?=
USE_READLINE ?= 0
READLINE_CPPFLAGS ?=
READLINE_LDFLAGS ?=
READLINE_LDLIBS ?= -lreadline

ifeq ($(USE_READLINE),1)
CPPFLAGS += -DUSE_READLINE $(READLINE_CPPFLAGS)
LDFLAGS += $(READLINE_LDFLAGS)
LDLIBS += $(READLINE_LDLIBS)
endif

.PHONY: all check clean run run-readline readline-check sanitize
all: repl

repl: src/repl.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) $(LDLIBS) -o $@

check: repl
	./tests/check.sh

readline-check: clean
	$(MAKE) USE_READLINE=1 check

sanitize: clean
	$(MAKE) CFLAGS='$(CFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
	        LDFLAGS='$(LDFLAGS) -fsanitize=address,undefined' check

run: repl
	./repl

run-readline: clean
	$(MAKE) USE_READLINE=1 repl
	./repl

clean:
	rm -f repl
