#include "Router.hpp"

#include <stdexcept>
#include <utility>

// [Implementation 3] Router가 handler 소유권을 넘겨받고 중복·할당 실패 시 부분 등록을 전부 되돌립니다.
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
