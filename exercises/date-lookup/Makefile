CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic

.PHONY: all test clean
all: date_lookup

date_lookup: src/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

test: date_lookup
	./tests/test.sh ./date_lookup

clean:
	rm -f date_lookup
