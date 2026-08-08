#include "Router.hpp"

#include <stdexcept>
#include <utility>

Router::Router()
    : handlers_()
{
    // TODO: 명령마다 구체 핸들러 하나를 생성해 등록하세요.
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
    static_cast<void>(command);
    // TODO: 등록된 핸들러나 0을 반환하세요.
    return 0;
}
