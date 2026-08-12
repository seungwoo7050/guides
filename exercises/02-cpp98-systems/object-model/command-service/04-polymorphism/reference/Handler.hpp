#ifndef HANDLER_HPP
#define HANDLER_HPP

#include "Model.hpp"

#include <string>

// [Implementation 2] 가상 소멸자를 가진 Handler 계약 뒤에 명령별 교체 가능한 동작을 배치합니다.
class Handler
{
public:
    virtual ~Handler() {}
    virtual std::string handle(
        const Request &request,
        Store &store) const = 0;
};

class PutHandler : public Handler
{
public:
    std::string handle(const Request &request, Store &store) const;
};

class GetHandler : public Handler
{
public:
    std::string handle(const Request &request, Store &store) const;
};

class DeleteHandler : public Handler
{
public:
    std::string handle(const Request &request, Store &store) const;
};

class CountHandler : public Handler
{
public:
    std::string handle(const Request &request, Store &store) const;
};

class QuitHandler : public Handler
{
public:
    std::string handle(const Request &request, Store &store) const;
};

#endif
