#include "Array.hpp"

int main()
{
    Array<int> values(1);
    const Array<int> &view = values;
    *view.begin() = 3; // const_iterator가 수정을 거부해야 합니다.
}
