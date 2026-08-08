#include "MiniVector.hpp"

#include <iostream>

int main()
{
    MiniVector<int> values;
    for (int i = 0; i < 10; ++i)
    {
        values.push_back(i);
        std::cout << "size=" << values.size()
                  << " capacity=" << values.capacity()
                  << '\n';
    }
}
