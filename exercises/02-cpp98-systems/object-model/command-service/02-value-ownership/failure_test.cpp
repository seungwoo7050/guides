#include "TextBuffer.hpp"
#include <cassert>
#include <iostream>
#include <new>
#include <string>

int main()
{
    TextBuffer target("old");
    TextBuffer source("new-value");
    const int before = TextBuffer::liveCount();
    TextBuffer::failAfter(0);
    try
    {
        target = source;
        assert(false && "allocation must fail");
    }
    catch (const std::bad_alloc &)
    {
    }
    TextBuffer::failAfter(-1);
    assert(std::string(target.c_str()) == "old");
    assert(std::string(source.c_str()) == "new-value");
    assert(TextBuffer::liveCount() == before);
    std::cout << "복사 실패 뒤 대상 값과 객체 수 보존 검사: 통과\n";
    return 0;
}
