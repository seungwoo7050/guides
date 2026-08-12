SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Werror -pedantic
TARGET := build/vector_sum

.PHONY: check report assembly clean

# [Implementation 5] check·report·assembly의 공개 workflow를 제공하고 report가 compiler별 진단 option을 고릅니다.
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
