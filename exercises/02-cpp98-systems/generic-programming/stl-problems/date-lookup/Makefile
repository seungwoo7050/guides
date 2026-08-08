CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
.PHONY: observe exercise-test test clean
observe: reference/date_lookup
	@printf '2024-01-05 | 4\n2024-01-12 | 2\n' | ./reference/date_lookup data.csv
exercise-test: skeleton/date_lookup
	@./test.sh ./skeleton/date_lookup
test: reference/date_lookup
	@./test.sh ./reference/date_lookup
skeleton/date_lookup: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
reference/date_lookup: reference/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
clean:
	rm -f skeleton/date_lookup reference/date_lookup
