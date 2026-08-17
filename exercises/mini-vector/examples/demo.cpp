#include "MiniVector.hpp"
#include <iostream>

// [Implementation 6] Capacity transition demo
// The demo exposes capacity transitions while exercising the public container API.
int main()
{
    MiniVector<int> values;
    for (int i = 0; i < 8; ++i)
    {
        values.push_back(i * 10);
        std::cout << "size=" << values.size()
                  << " capacity=" << values.capacity() << '\n';
    }
}
