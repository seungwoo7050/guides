CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic -O2
.PHONY: observe exercise-test test failure-test clean
observe: reference/cgi_runner
	@./reference/cgi_runner ./helpers/echo_cgi.py 1000 'hello cgi'
exercise-test: skeleton/cgi_runner
	@./test.sh ./skeleton/cgi_runner
test: reference/cgi_runner
	@./test.sh ./reference/cgi_runner
failure-test: reference/cgi_runner
	@./failure_test.sh ./reference/cgi_runner
skeleton/cgi_runner: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
reference/cgi_runner: reference/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
clean:
	rm -f skeleton/cgi_runner reference/cgi_runner
