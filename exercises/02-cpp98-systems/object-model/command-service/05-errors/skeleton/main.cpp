#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>

// TODO:
// 1. ParseError와 Conflict를 서로 다른 타입으로 정의하세요.
// 2. 파싱과 Store 갱신을 함수 또는 객체 경계로 분리하세요.
// 3. 최상위 경계에서 두 실패를 서로 다른 외부 응답으로 변환한다.

int main()
{
    std::map<std::string, std::string> data;
    std::string line;

    while (std::getline(std::cin, line))
    {
        try
        {
            std::istringstream input(line);
            std::string command;
            std::string key;
            std::string value;
            input >> command;

            if (command == "PUT" && input >> key >> value)
            {
                if (data.find(key) != data.end())
                    throw std::runtime_error("키가 이미 있습니다");
                data[key] = value;
                std::cout << "OK\n";
            }
            else if (command == "GET" && input >> key)
            {
                std::cout << (data.find(key) == data.end()
                    ? "NOT_FOUND"
                    : "VALUE " + data[key])
                          << '\n';
            }
            else if (command == "QUIT")
            {
                std::cout << "BYE\n";
                break;
            }
            else
            {
                throw std::runtime_error("요청이 올바르지 않습니다");
            }
        }
        catch (const std::exception &)
        {
            // 현재 구현은 문법 오류와 상태 충돌을 구분하지 못한다.
            std::cout << "BAD_REQUEST\n";
        }
    }

    return 0;
}
