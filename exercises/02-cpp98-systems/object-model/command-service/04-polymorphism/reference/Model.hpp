#ifndef MODEL_HPP
#define MODEL_HPP

#include <cstddef>
#include <map>
#include <string>
#include <vector>

// [Implementation 1] 명령과 인자를 Request로 만들고 Store를 handler들이 공유하는 상태 owner로 둡니다.
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
