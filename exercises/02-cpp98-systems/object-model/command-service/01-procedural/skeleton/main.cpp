#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

static std::vector<std::string> split(const std::string &line)
{
    std::vector<std::string> parts;
    // TODO: std::istringstream으로 공백 단위 토큰을 모두 수집하세요.
    static_cast<void>(line);
    return parts;
}

int main()
{
    std::map<std::string, std::string> store;
    std::string line;
    while (std::getline(std::cin, line))
    {
        const std::vector<std::string> parts = split(line);
        if (parts.empty())
            continue;
        // TODO: PUT, GET, DELETE, COUNT, LIST, QUIT을 비교용 구현과 같은 계약으로 처리하세요.
        static_cast<void>(store);
        std::cout << "BAD_REQUEST\n";
    }
    return 0;
}
