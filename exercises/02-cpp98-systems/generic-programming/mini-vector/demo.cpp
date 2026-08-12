#include "MiniVector.hpp"

#include <iostream>

// [Implementation 6] 연속 삽입에서 size와 capacity 전이를 출력해 growth policy를 좁게 관찰합니다.
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
