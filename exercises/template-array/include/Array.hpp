#ifndef TEMPLATE_ARRAY_HPP
#define TEMPLATE_ARRAY_HPP

#include <algorithm>
#include <cstddef>
#include <stdexcept>

// [Implementation 1] Fixed storage model
// Array owns fixed-size heap storage while preserving a valid empty state.
template <class T>
class Array
{
public:
    typedef T value_type;
    typedef T *iterator;
    typedef const T *const_iterator;

    Array() : data_(0), size_(0) {}

    explicit Array(std::size_t size)
        : data_(size != 0 ? new T[size] : 0), size_(size)
    {
    }

    // [Implementation 2] Deep-copy transaction
    // Deep-copy construction cleans failed storage and assignment commits by swap.
    Array(const Array &other)
        : data_(other.size_ != 0 ? new T[other.size_] : 0), size_(other.size_)
    {
        try
        {
            std::copy(other.begin(), other.end(), begin());
        }
        catch (...)
        {
            delete[] data_;
            data_ = 0;
            size_ = 0;
            throw;
        }
    }

    ~Array() { delete[] data_; }

    Array &operator=(Array other)
    {
        swap(other);
        return *this;
    }

    void swap(Array &other) throw()
    {
        std::swap(data_, other.data_);
        std::swap(size_, other.size_);
    }

    std::size_t size() const { return size_; }

    // [Implementation 3] Mutable and const range contract
    // Mutable and const access share one half-open iterator range over owned storage.
    T &operator[](std::size_t index) { return data_[index]; }
    const T &operator[](std::size_t index) const { return data_[index]; }

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

    iterator begin() { return data_; }
    const_iterator begin() const { return data_; }
    iterator end() { return size_ == 0 ? data_ : data_ + size_; }
    const_iterator end() const { return size_ == 0 ? data_ : data_ + size_; }

private:
    T *data_;
    std::size_t size_;
};

// [Implementation 4] Iterator-based apply algorithm
// apply depends only on iterator and callable contracts rather than a container type.
template <class Iterator, class Function>
void apply(Iterator first, Iterator last, Function function)
{
    for (; first != last; ++first)
        function(*first);
}

#endif
