CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic -O2
SKELETON_SRCS := $(wildcard skeleton/*.cpp)
.PHONY: observe exercise-test test failure-test clean
observe: reference/http_server
	@python3 tests.py ./reference/http_server --observe
exercise-test: skeleton/http_server
	@python3 tests.py ./skeleton/http_server
test: reference/http_server
	@python3 tests.py ./reference/http_server
failure-test: reference/http_server
	@python3 tests.py ./reference/http_server --failures
skeleton/http_server: $(SKELETON_SRCS)
	$(CXX) $(CXXFLAGS) -Iskeleton $(SKELETON_SRCS) -o $@
reference/http_server: reference/main.cpp reference/HttpParser.cpp reference/HttpParser.hpp
	$(CXX) $(CXXFLAGS) -Ireference reference/main.cpp reference/HttpParser.cpp -o $@
clean:
	rm -f skeleton/http_server reference/http_server
