#include "Array.hpp"
#include <iostream>

struct Print
{
    void operator()(int value) const { std::cout << value << '\n'; }
};

// [Implementation 5] Public API composition demo
// The demo composes Array storage with the iterator-based apply algorithm.
int main()
{
    Array<int> values(3);
    values[0] = 10; values[1] = 20; values[2] = 30;
    apply(values.begin(), values.end(), Print());
}
