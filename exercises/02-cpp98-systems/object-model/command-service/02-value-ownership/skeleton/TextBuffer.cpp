#include "TextBuffer.hpp"
#include <cstring>
#include <new>
#include <stdexcept>

int TextBuffer::allocationCountdown_ = -1;
int TextBuffer::liveCount_ = 0;

char *TextBuffer::allocate(std::size_t count)
{
    if (allocationCountdown_ == 0) throw std::bad_alloc();
    if (allocationCountdown_ > 0) --allocationCountdown_;
    return new char[count];
}

TextBuffer::TextBuffer() : data_(allocate(1)), size_(0) { data_[0] = '\0'; ++liveCount_; }
TextBuffer::TextBuffer(const char *text) : data_(0), size_(text ? std::strlen(text) : 0)
{
    data_ = allocate(size_ + 1);
    if (size_) std::memcpy(data_, text, size_);
    data_[size_] = '\0';
    ++liveCount_;
}

TextBuffer::TextBuffer(const TextBuffer &other) : data_(allocate(1)), size_(0)
{
    // TODO: other와 독립적인 깊은 복사본을 만드세요.
    static_cast<void>(other);
    data_[0] = '\0';
    ++liveCount_;
}

TextBuffer::~TextBuffer() { delete[] data_; --liveCount_; }

TextBuffer &TextBuffer::operator=(const TextBuffer &other)
{
    // TODO: 할당 실패 시 *this를 보존하는 대입을 구현하세요.
    static_cast<void>(other);
    data_[0] = '\0';
    size_ = 0;
    return *this;
}

const char *TextBuffer::c_str() const { return data_; }
std::size_t TextBuffer::size() const { return size_; }
void TextBuffer::set(std::size_t index, char value)
{
    if (index >= size_) throw std::out_of_range("TextBuffer::set");
    data_[index] = value;
}
void TextBuffer::swap(TextBuffer &other) throw()
{
    char *d = data_; data_ = other.data_; other.data_ = d;
    std::size_t s = size_; size_ = other.size_; other.size_ = s;
}
void TextBuffer::failAfter(int n) { allocationCountdown_ = n; }
int TextBuffer::liveCount() { return liveCount_; }
