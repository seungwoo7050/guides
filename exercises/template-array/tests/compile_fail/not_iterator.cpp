#include "Array.hpp"
struct Ignore { void operator()(int) const {} };
int main()
{
    apply(1, 3, Ignore());
}
