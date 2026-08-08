#include "Array.hpp"

#include <cassert>
#include <iostream>
#include <string>

struct Increment
{
    void operator()(int &value) const
    {
        ++value;
    }
};

int main()
{
    Array<int> values(3);
    values[0] = 1;
    values[1] = 2;
    values[2] = 3;

    apply(values.begin(), values.end(), Increment());
    assert(values[0] == 2 && values[2] == 4);

    Array<int> copy(values);
    copy[0] = 99;
    assert(values[0] == 2);

    Array<int> assigned;
    assigned = copy;
    assert(assigned.size() == 3 && assigned[0] == 99);

    const Array<int> &view = values;
    int sum = 0;
    for (Array<int>::const_iterator it = view.begin();
         it != view.end(); ++it)
    {
        sum += *it;
    }
    assert(sum == 9);

    bool threw = false;
    try
    {
        values.at(3);
    }
    catch (const std::out_of_range &)
    {
        threw = true;
    }
    assert(threw);

    Array<std::string> words(2);
    words[0] = "x";
    words[1] = "y";
    assert(words[1] == "y");

    std::cout << "template-array 검사: 통과\n";
}
