#ifndef POLLER_HPP
#define POLLER_HPP

#include <vector>

// [Implementation 1] platform event를 fd별 read/write/hangup/error의 이식 가능한 값 계약으로 정규화합니다.
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

// [Implementation 2] event loop는 platform 구체 타입 대신 factory가 돌려주는 Poller 소유권만 받습니다.
Poller *createPoller();

#endif
