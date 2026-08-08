#ifndef POLLER_HPP
#define POLLER_HPP

#include <vector>

struct PollEvent
{
    int fd;
    bool readable;
    bool writable;
    bool hangup;
    bool error;

    PollEvent()
        : fd(-1),
          readable(false),
          writable(false),
          hangup(false),
          error(false)
    {
    }
};

enum Interest
{
    InterestRead = 1,
    InterestWrite = 2
};

class Poller
{
public:
    virtual ~Poller() {}

    virtual void add(int fd, int interest) = 0;
    virtual void update(int fd, int interest) = 0;
    virtual void remove(int fd) = 0;
    virtual std::vector<PollEvent> wait(int timeoutMs) = 0;
};

Poller *createPoller();

#endif
