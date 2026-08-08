#include "Array.hpp"

struct Function
{
    void operator()(int &value) const
    {
        static_cast<void>(value);
    }
};

int main()
{
    apply(1, 3, Function()); // int는 iterator 계약을 만족하지 않는다.
}
