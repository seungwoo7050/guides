#ifndef MODEL_HPP
#define MODEL_HPP

#include <cstddef>
#include <map>
#include <string>
#include <vector>

struct Request
{
    std::string command;
    std::vector<std::string> args;
};

class Store
{
public:
    bool put(const std::string &key, const std::string &value);
    bool get(const std::string &key, std::string &value) const;
    bool erase(const std::string &key);
    std::size_t size() const;

private:
    std::map<std::string, std::string> data_;
};

Request parse(const std::string &line);

#endif
