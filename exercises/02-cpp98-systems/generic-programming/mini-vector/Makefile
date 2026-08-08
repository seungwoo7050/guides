CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: observe exercise-test test fail-copy clean
observe: reference/demo
	@./reference/demo
exercise-test: skeleton/tests
	@./skeleton/tests
test: reference/tests
	@./reference/tests
fail-copy: reference/failure
	@./reference/failure
skeleton/tests: tests.cpp skeleton/MiniVector.hpp ThrowOnCopy.hpp
	$(CXX) $(CXXFLAGS) -Iskeleton tests.cpp -o $@
reference/tests: tests.cpp reference/MiniVector.hpp ThrowOnCopy.hpp
	$(CXX) $(CXXFLAGS) -Ireference tests.cpp -o $@
reference/failure: failure.cpp reference/MiniVector.hpp ThrowOnCopy.hpp
	$(CXX) $(CXXFLAGS) -Ireference failure.cpp -o $@
reference/demo: demo.cpp reference/MiniVector.hpp
	$(CXX) $(CXXFLAGS) -Ireference demo.cpp -o $@
clean:
	rm -f skeleton/tests reference/tests reference/failure reference/demo
