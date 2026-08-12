#ifndef TEXTBUFFER_HPP
#define TEXTBUFFER_HPP

#include <cstddef>

// [Implementation 1] TextBuffer가 heap 문자열의 표현과 Rule of Three 공개 계약을 한 타입 안에 소유합니다.
class TextBuffer
{
public:
    TextBuffer();
    explicit TextBuffer(const char *text);
    TextBuffer(const TextBuffer &other);
    ~TextBuffer();
    TextBuffer &operator=(const TextBuffer &other);

    const char *c_str() const;
    std::size_t size() const;
    void set(std::size_t index, char value);
    void swap(TextBuffer &other) throw();

    static void failAfter(int allocations);
    static int liveCount();

private:
    char *data_;
    std::size_t size_;
    static int allocationCountdown_;
    static int liveCount_;

    static char *allocate(std::size_t count);
};

#endif
