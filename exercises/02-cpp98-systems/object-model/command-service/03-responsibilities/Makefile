CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
REFERENCE_SRCS := $(wildcard reference/*.cpp)
REFERENCE_LIBRARY_SRCS := $(filter-out reference/main.cpp,$(REFERENCE_SRCS))
SKELETON_SRCS := $(filter-out skeleton/legacy.cpp,$(wildcard skeleton/*.cpp))
.PHONY: observe exercise-test test interface-check clean
observe: skeleton/legacy_app
	@printf 'PUT a 1\nPUT b 2\nPUT c 3\nGET a\nCOUNT\nDELETE a\nCOUNT\nQUIT\n' | ./skeleton/legacy_app
exercise-test: skeleton/app
	@./test.sh ./skeleton/app
reference/app: $(REFERENCE_SRCS)
	$(CXX) $(CXXFLAGS) -Ireference $(REFERENCE_SRCS) -o $@
skeleton/app: $(SKELETON_SRCS)
	$(CXX) $(CXXFLAGS) -Iskeleton $(SKELETON_SRCS) -o $@
skeleton/legacy_app: skeleton/legacy.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
test: reference/app
	@./test.sh ./reference/app
interface-check: reference/interface_test
	@./reference/interface_test
reference/interface_test: interface_test.cpp $(REFERENCE_LIBRARY_SRCS)
	$(CXX) $(CXXFLAGS) -Ireference $^ -o $@
clean:
	rm -f skeleton/app skeleton/legacy_app reference/app reference/interface_test
