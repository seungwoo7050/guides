#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

// [Implementation 1] 한 입력 줄을 명령과 인자로 분리하되 저장 상태나 출력 정책은 알지 않게 합니다.
static std::vector<std::string> split(const std::string &line)
{
    std::istringstream input(line);
    std::vector<std::string> parts;
    std::string part;
    while (input >> part)
        parts.push_back(part);
    return parts;
}

// [Implementation 2] main이 store 상태를 소유하고 각 명령의 arity, 상태 변경과 외부 출력 계약을 한 흐름으로 연결합니다.
int main()
{
    std::map<std::string, std::string> store;
    std::string line;
    while (std::getline(std::cin, line))
    {
        const std::vector<std::string> parts = split(line);
        if (parts.empty())
            continue;
        if (parts[0] == "PUT" && parts.size() == 3)
        {
            store[parts[1]] = parts[2];
            std::cout << "OK\n";
        }
        else if (parts[0] == "GET" && parts.size() == 2)
        {
            const std::map<std::string, std::string>::const_iterator it = store.find(parts[1]);
            if (it == store.end())
                std::cout << "NOT_FOUND\n";
            else
                std::cout << "VALUE " << it->second << '\n';
        }
        else if (parts[0] == "DELETE" && parts.size() == 2)
        {
            if (store.erase(parts[1]) == 0)
                std::cout << "NOT_FOUND\n";
            else
                std::cout << "DELETED\n";
        }
        else if (parts[0] == "COUNT" && parts.size() == 1)
            std::cout << "COUNT " << store.size() << '\n';
        else if (parts[0] == "LIST" && parts.size() == 1)
        {
            for (std::map<std::string, std::string>::const_iterator it = store.begin(); it != store.end(); ++it)
                std::cout << it->first << '=' << it->second << '\n';
        }
        else if (parts[0] == "QUIT" && parts.size() == 1)
        {
            std::cout << "BYE\n";
            return 0;
        }
        else
            std::cout << "BAD_REQUEST\n";
    }
    return 0;
}
