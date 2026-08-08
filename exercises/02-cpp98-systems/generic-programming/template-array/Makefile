CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: observe exercise-test test compile-fail clean
observe: reference/demo
	@./reference/demo
exercise-test: skeleton/tests
	@./skeleton/tests
test: reference/tests
	@./reference/tests
compile-fail:
	@! $(CXX) $(CXXFLAGS) -Ireference compile_fail/modify_const.cpp -o /tmp/modify_const 2>/tmp/modify_const.err
	@! $(CXX) $(CXXFLAGS) -Ireference compile_fail/not_iterator.cpp -o /tmp/not_iterator 2>/tmp/not_iterator.err
	@echo '컴파일 실패 조건 검사: 통과'
skeleton/tests: tests.cpp skeleton/Array.hpp
	$(CXX) $(CXXFLAGS) -Iskeleton tests.cpp -o $@
reference/tests: tests.cpp reference/Array.hpp
	$(CXX) $(CXXFLAGS) -Ireference tests.cpp -o $@
reference/demo: demo.cpp reference/Array.hpp
	$(CXX) $(CXXFLAGS) -Ireference demo.cpp -o $@
clean:
	rm -f skeleton/tests reference/tests reference/demo /tmp/modify_const /tmp/not_iterator /tmp/*.err
