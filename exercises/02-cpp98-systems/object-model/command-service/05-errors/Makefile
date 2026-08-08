CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: observe exercise-test test fail-commit clean
observe: reference/app
	@printf 'PUT a 1\nPUT a 2\nGET\nBOGUS\nQUIT\n' | ./reference/app
exercise-test: skeleton/app
	@./test.sh ./skeleton/app
test: reference/app
	@./test.sh ./reference/app
skeleton/app: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
reference/app: reference/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
fail-commit: reference/commit_failure
	@./reference/commit_failure
reference/commit_failure: commit_failure.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
clean:
	rm -f skeleton/app reference/app reference/commit_failure
