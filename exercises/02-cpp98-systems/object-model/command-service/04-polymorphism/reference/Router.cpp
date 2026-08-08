#include "Router.hpp"

#include <stdexcept>
#include <utility>

Router::Router()
    : handlers_()
{
    try
    {
        add("PUT", new PutHandler());
        add("GET", new GetHandler());
        add("DELETE", new DeleteHandler());
        add("COUNT", new CountHandler());
        add("QUIT", new QuitHandler());
    }
    catch (...)
    {
        clear();
        throw;
    }
}

Router::~Router()
{
    clear();
}

void Router::add(const std::string &command, Handler *handler)
{
    if (handler == 0)
        throw std::invalid_argument("처리기가 비어 있습니다");

    bool transferred = false;
    try
    {
        const std::pair<
            std::map<std::string, Handler *>::iterator,
            bool> inserted = handlers_.insert(
                std::make_pair(command, handler));

        if (!inserted.second)
            throw std::logic_error("같은 명령의 처리기가 이미 등록되었습니다");
        transferred = true;
    }
    catch (...)
    {
        if (!transferred)
            delete handler;
        throw;
    }
}

void Router::clear()
{
    for (std::map<std::string, Handler *>::iterator it = handlers_.begin();
         it != handlers_.end(); ++it)
    {
        delete it->second;
    }
    handlers_.clear();
}

const Handler *Router::find(const std::string &command) const
{
    const std::map<std::string, Handler *>::const_iterator found
        = handlers_.find(command);
    return found == handlers_.end() ? 0 : found->second;
}
