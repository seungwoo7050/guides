#include "TextBuffer.hpp"
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

static std::vector<std::string> split(const std::string &line)
{
    std::istringstream input(line);
    std::vector<std::string> parts;
    std::string part;
    while (input >> part)
        parts.push_back(part);
    return parts;
}

int main()
{
    std::map<std::string, TextBuffer> store;
    std::string line;
    while (std::getline(std::cin, line))
    {
        const std::vector<std::string> p = split(line);
        if (p.empty()) continue;
        if (p[0] == "PUT" && p.size() == 3)
        {
            store[p[1]] = TextBuffer(p[2].c_str());
            std::cout << "OK\n";
        }
        else if (p[0] == "GET" && p.size() == 2)
        {
            const std::map<std::string, TextBuffer>::const_iterator it = store.find(p[1]);
            std::cout << (it == store.end() ? "NOT_FOUND" : std::string("VALUE ") + it->second.c_str()) << '\n';
        }
        else if (p[0] == "QUIT")
        {
            std::cout << "BYE\n";
            break;
        }
        else std::cout << "BAD_REQUEST\n";
    }
}
