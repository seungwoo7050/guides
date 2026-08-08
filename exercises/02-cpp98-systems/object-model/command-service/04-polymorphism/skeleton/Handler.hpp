#ifndef HANDLER_HPP
#define HANDLER_HPP

#include "Model.hpp"

#include <string>

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
