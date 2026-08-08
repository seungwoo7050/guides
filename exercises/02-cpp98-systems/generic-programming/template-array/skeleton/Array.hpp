#ifndef ARRAY_HPP
#define ARRAY_HPP

#include <algorithm>
#include <cstddef>
#include <stdexcept>

template <class T>
class Array
{
public:
    typedef T value_type;
    typedef T *iterator;
    typedef const T *const_iterator;

    Array()
        : data_(0), size_(0)
    {
    }

    explicit Array(std::size_t size)
        : data_(size != 0 ? new T[size] : 0), size_(size)
    {
    }

    Array(const Array &other)
        : data_(0), size_(0)
    {
        static_cast<void>(other);
        // TODO: 독립적인 깊은 복사본을 만드세요.
    }

    ~Array()
    {
        delete[] data_;
    }

    Array &operator=(Array other)
    {
        static_cast<void>(other);
        // TODO: 실패하지 않는 swap을 반영 단계로 사용하세요.
        return *this;
    }

    void swap(Array &other) throw()
    {
        std::swap(data_, other.data_);
        std::swap(size_, other.size_);
    }

    std::size_t size() const
    {
        return size_;
    }

    T &operator[](std::size_t index)
    {
        return data_[index];
    }

    const T &operator[](std::size_t index) const
    {
        return data_[index];
    }

    T &at(std::size_t index)
    {
        if (index >= size_)
            throw std::out_of_range("Array::at");
        return data_[index];
    }

    const T &at(std::size_t index) const
    {
        if (index >= size_)
            throw std::out_of_range("Array::at");
        return data_[index];
    }

    iterator begin()
    {
        return data_;
    }

    const_iterator begin() const
    {
        return data_;
    }

    iterator end()
    {
        return size_ == 0 ? data_ : data_ + size_;
    }

    const_iterator end() const
    {
        return size_ == 0 ? data_ : data_ + size_;
    }

private:
    T *data_;
    std::size_t size_;
};

template <class Iterator, class Function>
void apply(Iterator first, Iterator last, Function function)
{
    static_cast<void>(first);
    static_cast<void>(last);
    static_cast<void>(function);
    // TODO: [first, last) 범위의 모든 원소에 함수를 적용하세요.
}

#endif
