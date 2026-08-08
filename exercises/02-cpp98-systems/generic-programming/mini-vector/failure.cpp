#include "MiniVector.hpp"
#include "ThrowOnCopy.hpp"

#include <cassert>
#include <iostream>

int ThrowOnCopy::live = 0;
int ThrowOnCopy::copiesBeforeThrow = -1;

static void verifyReserveRollback()
{
    MiniVector<ThrowOnCopy> values;
    values.push_back(ThrowOnCopy(1));
    values.push_back(ThrowOnCopy(2));

    const std::size_t oldSize = values.size();
    const std::size_t oldCapacity = values.capacity();
    const int liveBefore = ThrowOnCopy::live;

    ThrowOnCopy::copiesBeforeThrow = 1;
    try
    {
        values.reserve(oldCapacity + 10);
        assert(false);
    }
    catch (const std::runtime_error &)
    {
    }
    ThrowOnCopy::copiesBeforeThrow = -1;

    assert(values.size() == oldSize);
    assert(values.capacity() == oldCapacity);
    assert(values[0].value == 1 && values[1].value == 2);
    assert(ThrowOnCopy::live == liveBefore);
}

static void verifyPushBackRollback()
{
    MiniVector<ThrowOnCopy> values;
    values.push_back(ThrowOnCopy(10));
    values.push_back(ThrowOnCopy(20));

    const std::size_t oldSize = values.size();
    const std::size_t oldCapacity = values.capacity();
    const int liveBefore = ThrowOnCopy::live;
    const ThrowOnCopy appended(30);

    // 기존 두 원소 복사는 성공하고 마지막 추가 복사에서 실패합니다.
    ThrowOnCopy::copiesBeforeThrow = 2;
    try
    {
        values.push_back(appended);
        assert(false);
    }
    catch (const std::runtime_error &)
    {
    }
    ThrowOnCopy::copiesBeforeThrow = -1;

    assert(values.size() == oldSize);
    assert(values.capacity() == oldCapacity);
    assert(values[0].value == 10 && values[1].value == 20);
    assert(ThrowOnCopy::live == liveBefore + 1); // appended 지역 객체
}

int main()
{
    verifyReserveRollback();
    assert(ThrowOnCopy::live == 0);

    verifyPushBackRollback();
    assert(ThrowOnCopy::live == 0);

    std::cout << "재할당 실패 뒤 상태 복원 검사: 통과\n";
}
