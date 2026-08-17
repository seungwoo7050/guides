#include <cerrno>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <string>

// [Implementation 1] Total operand parsing
// Operand parsing consumes the complete token and enforces the int range.
static int parseInteger(const std::string &text)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text.c_str(), &end, 10);
    if (errno != 0 || end == text.c_str() || *end != '\0' ||
        value < INT_MIN || value > INT_MAX)
    {
        throw std::runtime_error("invalid integer");
    }
    return static_cast<int>(value);
}

// [Implementation 2] Checked arithmetic
// Arithmetic validation preserves operand order and rejects errors before stack mutation.
static int apply(char operation, int left, int right)
{
    if (operation == '+')
    {
        if ((right > 0 && left > INT_MAX - right) ||
            (right < 0 && left < INT_MIN - right))
            throw std::runtime_error("integer overflow");
        return left + right;
    }
    if (operation == '-')
    {
        if ((right < 0 && left > INT_MAX + right) ||
            (right > 0 && left < INT_MIN + right))
            throw std::runtime_error("integer overflow");
        return left - right;
    }
    if (operation == '*')
    {
        if (left == 0 || right == 0)
            return 0;
        if ((left == -1 && right == INT_MIN) ||
            (right == -1 && left == INT_MIN))
            throw std::runtime_error("integer overflow");
        if (left > 0)
        {
            if ((right > 0 && left > INT_MAX / right) ||
                (right < 0 && right < INT_MIN / left))
                throw std::runtime_error("integer overflow");
        }
        else
        {
            if ((right > 0 && left < INT_MIN / right) ||
                (right < 0 && left < INT_MAX / right))
                throw std::runtime_error("integer overflow");
        }
        return left * right;
    }

    if (right == 0)
        throw std::runtime_error("division by zero");
    if (left == INT_MIN && right == -1)
        throw std::runtime_error("integer overflow");
    return left / right;
}

static bool isOperator(const std::string &token)
{
    return token.size() == 1 &&
           std::string("+-*/").find(token[0]) != std::string::npos;
}

// [Implementation 3] Stack reduction
// Tokens reduce a stack so every operator consumes exactly two operands.
int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "usage: rpn \"expression\"\n";
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
                throw std::runtime_error("insufficient operands");

            const int right = values.top(); values.pop();
            const int left = values.top(); values.pop();
            values.push(apply(token[0], left, right));
        }

        // [Implementation 4] Final expression invariant
        // A complete expression must leave exactly one result on the stack.
        if (values.size() != 1)
            throw std::runtime_error("expression must produce one result");
        std::cout << values.top() << '\n';
    }
    catch (const std::exception &error)
    {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
