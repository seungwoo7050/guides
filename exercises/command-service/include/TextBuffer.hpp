#ifndef COMMAND_SERVICE_TEXT_BUFFER_HPP
#define COMMAND_SERVICE_TEXT_BUFFER_HPP

#include <cstddef>

// [Implementation 2] Owned text value
// TextBuffer is the sole owner of a null-terminated heap string.
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
