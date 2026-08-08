CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
SKELETON_SRCS := $(wildcard skeleton/*.cpp)
REFERENCE_SRCS := $(wildcard reference/*.cpp)
.PHONY: observe exercise-test test fail-nonvirtual clean
observe: reference/app
	@printf 'PUT a 1\nGET a\nCOUNT\nDELETE a\nQUIT\n' | ./reference/app
exercise-test: skeleton/app
	@./test.sh ./skeleton/app
test: reference/app
	@./test.sh ./reference/app
skeleton/app: $(SKELETON_SRCS)
	$(CXX) $(CXXFLAGS) -Iskeleton $(SKELETON_SRCS) -o $@
reference/app: $(REFERENCE_SRCS)
	$(CXX) $(CXXFLAGS) -Ireference $(REFERENCE_SRCS) -o $@
fail-nonvirtual:
	@! $(CXX) $(CXXFLAGS) -Wnon-virtual-dtor -Wdelete-non-virtual-dtor nonvirtual_delete.cpp -o /tmp/nonvirtual_delete 2>/tmp/nonvirtual_delete.err
	@grep -E 'non-virtual|virtual' /tmp/nonvirtual_delete.err >/dev/null
	@echo '가상 소멸자가 없는 다형 기본 클래스 포인터 삭제를 컴파일러가 거부했습니다'
clean:
	rm -f skeleton/app reference/app /tmp/nonvirtual_delete /tmp/nonvirtual_delete.err
