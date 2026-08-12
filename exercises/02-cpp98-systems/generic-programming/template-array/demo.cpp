#include "Array.hpp"

#include <iostream>

struct Print
{
    void operator()(const int &value) const
    {
        std::cout << value << ' ';
    }
};

// [Implementation 5] 완성된 Array를 채우고 iterator 기반 apply로 관찰 가능한 순회 결과를 만듭니다.
int main()
{
    Array<int> values(4);
    for (std::size_t i = 0; i < values.size(); ++i)
        values[i] = static_cast<int>(i * i);

    apply(values.begin(), values.end(), Print());
    std::cout << '\n';
}
