#ifndef COMMAND_SERVICE_HANDLER_HPP
#define COMMAND_SERVICE_HANDLER_HPP

#include "Request.hpp"
#include "Response.hpp"
#include "Store.hpp"

// [Implementation 6] Polymorphic handler contract
// A virtual handler contract isolates command behavior behind one dispatch interface.
class Handler
{
public:
    virtual ~Handler() {}
    virtual Response handle(const Request &request, Store &store) const = 0;
};

class PutHandler : public Handler
{
public:
    Response handle(const Request &request, Store &store) const;
};

class GetHandler : public Handler
{
public:
    Response handle(const Request &request, Store &store) const;
};

class DeleteHandler : public Handler
{
public:
    Response handle(const Request &request, Store &store) const;
};

class CountHandler : public Handler
{
public:
    Response handle(const Request &request, Store &store) const;
};

class ListHandler : public Handler
{
public:
    Response handle(const Request &request, Store &store) const;
};

class QuitHandler : public Handler
{
public:
    Response handle(const Request &request, Store &store) const;
};

#endif
