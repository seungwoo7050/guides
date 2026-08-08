CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic -O2

override REFERENCE := reference/integrated_http_server
override SKELETON := skeleton/integrated_http_server
override REFERENCE_SOURCES := \
	reference/main.cpp \
	reference/HttpParser.cpp \
	reference/Router.cpp \
	reference/CgiRunner.cpp

.PHONY: check observe exercise-test test failure-test sanitize clean

check: exercise-test test failure-test

observe: $(REFERENCE)
	@python3 tests.py ./$(REFERENCE) --observe

exercise-test: $(SKELETON)
	@python3 tests.py ./$(SKELETON) --skeleton

test: $(REFERENCE)
	@python3 tests.py ./$(REFERENCE)

failure-test: $(REFERENCE)
	@python3 tests.py ./$(REFERENCE) --failures

$(REFERENCE): $(REFERENCE_SOURCES) \
	reference/HttpParser.hpp reference/Router.hpp reference/CgiRunner.hpp
	$(CXX) $(CXXFLAGS) -Ireference $(REFERENCE_SOURCES) -o $@

$(SKELETON): skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

sanitize:
	@$(MAKE) clean
	@$(MAKE) \
		CXXFLAGS='-std=c++98 -Wall -Wextra -Werror -pedantic -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
		check

clean:
	rm -f ./reference/integrated_http_server ./skeleton/integrated_http_server
	find . -type d -name '*.dSYM' -prune -exec rm -rf {} +
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
