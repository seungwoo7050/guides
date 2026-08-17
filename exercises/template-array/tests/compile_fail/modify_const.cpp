#include "Array.hpp"
int main()
{
    const Array<int> values(1);
    *values.begin() = 42;
}
