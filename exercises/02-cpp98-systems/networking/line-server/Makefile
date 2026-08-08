CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic -O2
override UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
override POLLER_SOURCE := reference/Poller_epoll.cpp
else ifeq ($(UNAME_S),Darwin)
override POLLER_SOURCE := reference/Poller_kqueue.cpp
else
$(error unsupported OS: $(UNAME_S))
endif
override REFERENCE_SRCS := reference/main.cpp $(POLLER_SOURCE)
override REFERENCE_OBJS := $(REFERENCE_SRCS:.cpp=.o)
override DEPENDENCIES := $(REFERENCE_OBJS:.o=.d)
override BUILD_ARTIFACTS := \
	reference/main.o reference/main.d \
	reference/Poller_epoll.o reference/Poller_epoll.d \
	reference/Poller_kqueue.o reference/Poller_kqueue.d
.PHONY: observe test stress backpressure leak-check skeleton-server clean
observe: reference/line_server
	@python3 tests.py ./reference/line_server --observe
test: reference/line_server
	@python3 tests.py ./reference/line_server
stress: reference/line_server
	@python3 tests.py ./reference/line_server --stress
backpressure: reference/line_server
	@python3 tests.py ./reference/line_server --backpressure
leak-check: reference/line_server
	@python3 tests.py ./reference/line_server --leak-check
skeleton-server: skeleton/blocking_server
skeleton/blocking_server: skeleton/main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
reference/line_server: $(REFERENCE_OBJS)
	$(CXX) $(CXXFLAGS) $(REFERENCE_OBJS) -o $@
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -MMD -MP -Ireference -c $< -o $@
clean:
	rm -f ./reference/line_server ./skeleton/blocking_server \
		./reference/main.o ./reference/main.d \
		./reference/Poller_epoll.o ./reference/Poller_epoll.d \
		./reference/Poller_kqueue.o ./reference/Poller_kqueue.d
-include $(DEPENDENCIES)
