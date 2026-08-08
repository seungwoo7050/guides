CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: observe exercise-test test clean
observe: reference/rpn
	@./reference/rpn '3 4 + 2 *'
exercise-test: skeleton/rpn
	@./test.sh ./skeleton/rpn
test: reference/rpn
	@./test.sh ./reference/rpn
skeleton/rpn: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
reference/rpn: reference/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
clean:
	rm -f skeleton/rpn reference/rpn
