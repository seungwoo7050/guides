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
    std::map<std::string, std::string> data;
    std::string line;

    while (std::getline(std::cin, line))
    {
        const std::vector<std::string> parts = split(line);

        if (parts.size() == 3 && parts[0] == "PUT")
        {
            const bool isNew = data.find(parts[1]) == data.end();
            if (isNew && data.size() >= 2)
            {
                std::cout << "FULL\n";
            }
            else
            {
                data[parts[1]] = parts[2];
                std::cout << "OK\n";
            }
        }
        else if (parts.size() == 2 && parts[0] == "GET")
        {
            const std::map<std::string, std::string>::const_iterator found
                = data.find(parts[1]);
            if (found == data.end())
                std::cout << "NOT_FOUND\n";
            else
                std::cout << "VALUE " << found->second << '\n';
        }
        else if (parts.size() == 2 && parts[0] == "DELETE")
        {
            std::cout << (data.erase(parts[1]) ? "DELETED" : "NOT_FOUND")
                      << '\n';
        }
        else if (parts.size() == 1 && parts[0] == "COUNT")
        {
            std::cout << "COUNT " << data.size() << '\n';
        }
        else if (parts.size() == 1 && parts[0] == "QUIT")
        {
            std::cout << "BYE\n";
            break;
        }
        else
        {
            std::cout << "BAD_REQUEST\n";
        }
    }
}
