CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
CPPFLAGS := -Iinclude
SOURCES := src/main.cpp src/HttpParser.cpp src/Router.cpp src/CgiRunner.cpp
COMPONENT_SOURCES := tests/component_tests.cpp src/HttpParser.cpp src/Router.cpp

.PHONY: all test integration-test failure-test clean
all: http_server

http_server: $(SOURCES) include/HttpParser.hpp include/Router.hpp include/CgiRunner.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $(SOURCES) -o $@

tests/component_tests: $(COMPONENT_SOURCES) include/HttpParser.hpp include/Router.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $(COMPONENT_SOURCES) -o $@

test: http_server tests/component_tests
	./tests/component_tests
	python3 tests/test_server.py ./http_server

integration-test: http_server
	python3 tests/test_server.py ./http_server --normal

failure-test: http_server
	python3 tests/test_server.py ./http_server --failures

clean:
	rm -f http_server tests/component_tests
