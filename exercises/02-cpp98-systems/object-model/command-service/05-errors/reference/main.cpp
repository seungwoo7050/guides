#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

class ParseError : public std::runtime_error
{
public:
    explicit ParseError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

class Conflict : public std::runtime_error
{
public:
    explicit Conflict(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

struct Request
{
    std::string command;
    std::vector<std::string> args;
};

static Request parse(const std::string &line)
{
    Request request;
    std::istringstream input(line);
    if (!(input >> request.command))
        throw ParseError("요청이 비어 있습니다");

    std::string argument;
    while (input >> argument)
        request.args.push_back(argument);

    if (request.command == "PUT" && request.args.size() != 2)
        throw ParseError("PUT에는 키와 값이 필요합니다");
    if (request.command == "GET" && request.args.size() != 1)
        throw ParseError("GET에는 키 하나가 필요합니다");
    if (request.command == "QUIT" && !request.args.empty())
        throw ParseError("QUIT에는 인자를 지정할 수 없습니다");

    if (request.command != "PUT"
        && request.command != "GET"
        && request.command != "QUIT")
    {
        throw ParseError("알 수 없는 명령입니다");
    }

    return request;
}

class Store
{
public:
    void putNew(const std::string &key, const std::string &value)
    {
        if (data_.find(key) != data_.end())
            throw Conflict("키가 이미 있습니다");
        data_.insert(std::make_pair(key, value));
    }

    bool get(const std::string &key, std::string &value) const
    {
        const std::map<std::string, std::string>::const_iterator found
            = data_.find(key);
        if (found == data_.end())
            return false;

        value = found->second;
        return true;
    }

private:
    std::map<std::string, std::string> data_;
};

int main()
{
    Store store;
    std::string line;

    while (std::getline(std::cin, line))
    {
        try
        {
            const Request request = parse(line);

            if (request.command == "PUT")
            {
                store.putNew(request.args[0], request.args[1]);
                std::cout << "OK\n";
            }
            else if (request.command == "GET")
            {
                std::string value;
                std::cout << (store.get(request.args[0], value)
                    ? "VALUE " + value
                    : "NOT_FOUND")
                          << '\n';
            }
            else
            {
                std::cout << "BYE\n";
                break;
            }
        }
        catch (const ParseError &)
        {
            std::cout << "BAD_REQUEST\n";
        }
        catch (const Conflict &)
        {
            std::cout << "CONFLICT\n";
        }
        catch (const std::exception &)
        {
            // 내부 진단 문자열을 외부 응답에 그대로 노출하지 않는다.
            std::cout << "INTERNAL_ERROR\n";
        }
    }

    return 0;
}
