CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic

.PHONY: observe exercise-test test fail-copy clean

observe: reference/app reference/text_buffer_test
	@./reference/text_buffer_test
	@printf 'PUT name alice\nGET name\nQUIT\n' | ./reference/app

exercise-test: skeleton/app skeleton/text_buffer_test
	@./skeleton/text_buffer_test
	@./test_app.sh ./skeleton/app

test: reference/app reference/text_buffer_test
	@./reference/text_buffer_test
	@./test_app.sh ./reference/app

fail-copy: reference/failure_test
	@./reference/failure_test

skeleton/app: skeleton/main.cpp skeleton/TextBuffer.cpp skeleton/TextBuffer.hpp
	$(CXX) $(CXXFLAGS) skeleton/main.cpp skeleton/TextBuffer.cpp -o $@
skeleton/text_buffer_test: test_textbuffer.cpp skeleton/TextBuffer.cpp skeleton/TextBuffer.hpp
	$(CXX) $(CXXFLAGS) -Iskeleton test_textbuffer.cpp skeleton/TextBuffer.cpp -o $@
reference/app: reference/main.cpp reference/TextBuffer.cpp reference/TextBuffer.hpp
	$(CXX) $(CXXFLAGS) reference/main.cpp reference/TextBuffer.cpp -o $@
reference/text_buffer_test: test_textbuffer.cpp reference/TextBuffer.cpp reference/TextBuffer.hpp
	$(CXX) $(CXXFLAGS) -Ireference test_textbuffer.cpp reference/TextBuffer.cpp -o $@
reference/failure_test: failure_test.cpp reference/TextBuffer.cpp reference/TextBuffer.hpp
	$(CXX) $(CXXFLAGS) -Ireference failure_test.cpp reference/TextBuffer.cpp -o $@

clean:
	rm -f skeleton/app skeleton/text_buffer_test reference/app reference/text_buffer_test reference/failure_test
