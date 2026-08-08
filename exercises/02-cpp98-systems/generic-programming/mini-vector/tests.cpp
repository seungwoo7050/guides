#include "MiniVector.hpp"
#include "ThrowOnCopy.hpp"

#include <cassert>
#include <iostream>

int ThrowOnCopy::live = 0;
int ThrowOnCopy::copiesBeforeThrow = -1;

int main()
{
    MiniVector<int> values;
    for (int i = 0; i < 20; ++i)
        values.push_back(i);

    assert(values.size() == 20);
    assert(values[19] == 19);

    MiniVector<int> copy(values);
    copy[0] = 99;
    assert(values[0] == 0);

    MiniVector<int> assigned;
    assigned = copy;
    assert(assigned[0] == 99);

    bool threw = false;
    try
    {
        values.at(20);
    }
    catch (const std::out_of_range &)
    {
        threw = true;
    }
    assert(threw);

    // value가 현재 저장소의 원소를 참조해도 재할당 전에 사라지면 안 됩니다.
    MiniVector<int> aliasing;
    aliasing.push_back(7);
    assert(aliasing.size() == aliasing.capacity());
    aliasing.push_back(aliasing[0]);
    assert(aliasing.size() == 2);
    assert(aliasing[0] == 7 && aliasing[1] == 7);

    std::cout << "mini-vector 검사: 통과\n";
}
