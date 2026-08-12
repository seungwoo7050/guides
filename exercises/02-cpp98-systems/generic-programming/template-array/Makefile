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
	@temporary=$$(mktemp -d "$${TMPDIR:-/tmp}/guide-cpp-template-array.XXXXXX") || exit 1; \
	trap 'rm -rf "$$temporary"' 0 1 2 15; \
	if $(CXX) $(CXXFLAGS) -Ireference compile_fail/modify_const.cpp \
		-o "$$temporary/modify_const" 2>"$$temporary/modify_const.err"; then \
		echo 'const 원소 수정 코드가 예상과 달리 컴파일되었습니다' >&2; exit 1; \
	fi; \
	if $(CXX) $(CXXFLAGS) -Ireference compile_fail/not_iterator.cpp \
		-o "$$temporary/not_iterator" 2>"$$temporary/not_iterator.err"; then \
		echo '반복자가 아닌 타입이 예상과 달리 컴파일되었습니다' >&2; exit 1; \
	fi; \
	echo '컴파일 실패 조건 검사: 통과'
skeleton/tests: tests.cpp skeleton/Array.hpp
	$(CXX) $(CXXFLAGS) -Iskeleton tests.cpp -o $@
reference/tests: tests.cpp reference/Array.hpp
	$(CXX) $(CXXFLAGS) -Ireference tests.cpp -o $@
reference/demo: demo.cpp reference/Array.hpp
	$(CXX) $(CXXFLAGS) -Ireference demo.cpp -o $@
clean:
	rm -f skeleton/tests reference/tests reference/demo
