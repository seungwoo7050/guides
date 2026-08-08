CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic -O2
.PHONY: observe exercise-test test randomized-test clean
observe: reference/sorter
	@./reference/sorter 9 3 7 1 8 2 6 5 4
exercise-test: skeleton/sorter
	@./test.sh ./skeleton/sorter
test: reference/sorter
	@./test.sh ./reference/sorter
randomized-test: reference/sorter
	@python3 randomized_test.py ./reference/sorter
skeleton/sorter: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
reference/sorter: reference/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
clean:
	rm -f skeleton/sorter reference/sorter
