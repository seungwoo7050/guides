CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic

.PHONY: observe exercise exercise-test test clean

observe: reference/app
	@printf 'PUT name alice\nGET name\nCOUNT\nDELETE name\nGET name\nQUIT\n' | ./reference/app

exercise: skeleton/app

exercise-test: skeleton/app
	@./test.sh ./skeleton/app

test: reference/app
	@./test.sh ./reference/app

skeleton/app: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

reference/app: reference/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -f skeleton/app reference/app
