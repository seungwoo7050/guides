CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: all test clean
all: rpn
rpn: src/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
test: rpn
	./tests/test.sh ./rpn
clean:
	rm -f rpn
