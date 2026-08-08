#include <cerrno>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <string>

static int parseInteger(const std::string &text)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text.c_str(), &end, 10);

    if (errno != 0 || end == text.c_str() || *end != '\0'
        || value < INT_MIN || value > INT_MAX)
    {
        throw std::runtime_error("숫자가 올바르지 않습니다");
    }
    return static_cast<int>(value);
}

static int apply(char operation, int left, int right)
{
    long result = 0;

    if (operation == '+')
        result = static_cast<long>(left) + right;
    else if (operation == '-')
        result = static_cast<long>(left) - right;
    else if (operation == '*')
        result = static_cast<long>(left) * right;
    else
    {
        if (right == 0)
            throw std::runtime_error("0으로 나눌 수 없습니다");
        if (left == INT_MIN && right == -1)
            throw std::runtime_error("정수 범위를 벗어났습니다");
        result = left / right;
    }

    if (result < INT_MIN || result > INT_MAX)
        throw std::runtime_error("정수 범위를 벗어났습니다");
    return static_cast<int>(result);
}

static bool isOperator(const std::string &token)
{
    return token.size() == 1
        && std::string("+-*/").find(token[0]) != std::string::npos;
}

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "사용법: rpn 수식\n";
        return 1;
    }

    try
    {
        std::istringstream input(argv[1]);
        std::stack<int> values;
        std::string token;

        while (input >> token)
        {
            if (!isOperator(token))
            {
                values.push(parseInteger(token));
                continue;
            }

            if (values.size() < 2)
                throw std::runtime_error("연산에 필요한 피연산자가 부족합니다");

            const int right = values.top();
            values.pop();
            const int left = values.top();
            values.pop();
            values.push(apply(token[0], left, right));
        }

        if (values.size() != 1)
            throw std::runtime_error("수식 계산을 마친 뒤 값이 하나만 남아야 합니다");

        std::cout << values.top() << '\n';
    }
    catch (const std::exception &error)
    {
        std::cerr << "오류: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
