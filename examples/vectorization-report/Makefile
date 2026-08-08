SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Werror -pedantic
TARGET := build/vector_sum

.PHONY: check report assembly clean

$(TARGET): vector_sum.c
	@mkdir -p build
	$(CC) $(CFLAGS) $< -lm -o $@

check: $(TARGET)
	@./$(TARGET)

report:
	@CC="$(CC)" ./report.sh

assembly:
	@mkdir -p build
	$(CC) $(CFLAGS) -S vector_sum.c -o build/vector_sum.s
	@printf '어셈블리 파일: build/vector_sum.s\n'

clean:
	@rm -rf build
