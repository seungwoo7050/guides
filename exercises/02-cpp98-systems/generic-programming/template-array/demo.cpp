#include "Array.hpp"

#include <iostream>

struct Print
{
    void operator()(const int &value) const
    {
        std::cout << value << ' ';
    }
};

int main()
{
    Array<int> values(4);
    for (std::size_t i = 0; i < values.size(); ++i)
        values[i] = static_cast<int>(i * i);

    apply(values.begin(), values.end(), Print());
    std::cout << '\n';
}
