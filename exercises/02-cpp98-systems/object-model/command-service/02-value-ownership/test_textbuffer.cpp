#include "TextBuffer.hpp"
#include <cassert>
#include <iostream>

int main()
{
    TextBuffer first("alpha");
    TextBuffer second(first);
    second.set(0, 'A');
    assert(std::string(first.c_str()) == "alpha");
    assert(std::string(second.c_str()) == "Alpha");

    TextBuffer third("old");
    third = first;
    assert(std::string(third.c_str()) == "alpha");
    TextBuffer &same = third;
    third = same;
    assert(std::string(third.c_str()) == "alpha");
    assert(first.size() == 5);
    std::cout << "TextBuffer 값 의미론 검사: 통과\n";
    return 0;
}
