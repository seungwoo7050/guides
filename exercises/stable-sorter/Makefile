CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: all test clean
all: stable_sorter
stable_sorter: src/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
test: stable_sorter
	./tests/test.sh ./stable_sorter
	python3 ./tests/randomized_test.py ./stable_sorter
clean:
	rm -f stable_sorter
