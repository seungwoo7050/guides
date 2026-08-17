CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
CPPFLAGS := -Iinclude

.PHONY: all test compile-fail clean
all: demo

demo: examples/demo.cpp include/Array.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $< -o $@

tests/array_tests: tests/array_tests.cpp include/Array.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $< -o $@

test: tests/array_tests compile-fail
	./tests/array_tests

compile-fail:
	@if $(CXX) $(CXXFLAGS) $(CPPFLAGS) tests/compile_fail/modify_const.cpp -o /tmp/template-array-modify-const 2>/dev/null; then echo "modify_const.cpp unexpectedly compiled"; rm -f /tmp/template-array-modify-const; exit 1; fi
	@if $(CXX) $(CXXFLAGS) $(CPPFLAGS) tests/compile_fail/not_iterator.cpp -o /tmp/template-array-not-iterator 2>/dev/null; then echo "not_iterator.cpp unexpectedly compiled"; rm -f /tmp/template-array-not-iterator; exit 1; fi

clean:
	rm -f demo tests/array_tests
