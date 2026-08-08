SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
TARGET := build/false_sharing

.PHONY: check benchmark clean

$(TARGET): false_sharing.c
	@mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -pthread -o $@

check: $(TARGET)
	@./$(TARGET) 2 100000

benchmark: $(TARGET)
	@./$(TARGET) 2 10000000

clean:
	@rm -rf build
