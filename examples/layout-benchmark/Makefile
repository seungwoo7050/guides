SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
TARGET := build/layout_benchmark

.PHONY: check benchmark clean

$(TARGET): layout_benchmark.c
	@mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: $(TARGET)
	@./$(TARGET) 128 96 2

benchmark: $(TARGET)
	@./$(TARGET) 2048 2048 4

clean:
	@rm -rf build
