CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: observe exercise-test test failure-test clean
observe: reference/demo
	@./reference/demo
exercise-test: skeleton/tests
	@./skeleton/tests
test: reference/tests
	@./reference/tests
failure-test: reference/tests
	@./reference/tests --failures
skeleton/tests: tests.cpp skeleton/HttpParser.cpp skeleton/HttpParser.hpp
	$(CXX) $(CXXFLAGS) -Iskeleton tests.cpp skeleton/HttpParser.cpp -o $@
reference/tests: tests.cpp reference/HttpParser.cpp reference/HttpParser.hpp
	$(CXX) $(CXXFLAGS) -Ireference tests.cpp reference/HttpParser.cpp -o $@
reference/demo: demo.cpp reference/HttpParser.cpp reference/HttpParser.hpp
	$(CXX) $(CXXFLAGS) -Ireference demo.cpp reference/HttpParser.cpp -o $@
clean:
	rm -f skeleton/tests reference/tests reference/demo
