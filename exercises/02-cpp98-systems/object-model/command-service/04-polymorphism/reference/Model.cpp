#include "Model.hpp"

#include <sstream>

bool Store::put(const std::string &key, const std::string &value)
{
    data_[key] = value;
    return true;
}

bool Store::get(const std::string &key, std::string &value) const
{
    const std::map<std::string, std::string>::const_iterator found
        = data_.find(key);
    if (found == data_.end())
        return false;

    value = found->second;
    return true;
}

bool Store::erase(const std::string &key)
{
    return data_.erase(key) != 0;
}

std::size_t Store::size() const
{
    return data_.size();
}

Request parse(const std::string &line)
{
    Request request;
    std::istringstream input(line);
    input >> request.command;

    std::string argument;
    while (input >> argument)
        request.args.push_back(argument);

    return request;
}
