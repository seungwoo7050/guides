SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
TARGET := build/branch_benchmark

.PHONY: check benchmark assembly clean

$(TARGET): branch_benchmark.c
	@mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: $(TARGET)
	@./$(TARGET) 200000

benchmark: $(TARGET)
	@./$(TARGET) 16000000

assembly:
	@mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -S branch_benchmark.c -o build/branch_benchmark.s
	@printf '어셈블리 파일: build/branch_benchmark.s\n'

clean:
	@rm -rf build
