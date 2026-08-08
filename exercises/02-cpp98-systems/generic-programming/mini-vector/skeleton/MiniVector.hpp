#ifndef MINIVECTOR_HPP
#define MINIVECTOR_HPP

#include <algorithm>
#include <cstddef>
#include <memory>
#include <stdexcept>

template <class T>
class MiniVector
{
public:
    typedef T *iterator;
    typedef const T *const_iterator;

    MiniVector()
        : data_(0), size_(0), capacity_(0), allocator_()
    {
    }

    MiniVector(const MiniVector &other)
        : data_(0), size_(0), capacity_(0), allocator_()
    {
        static_cast<void>(other);
        // TODO: 후보 저장 공간을 확보하고 생성된 원소만 복사하세요.
    }

    ~MiniVector()
    {
        clear();
        if (data_ != 0)
            allocator_.deallocate(data_, capacity_);
    }

    MiniVector &operator=(MiniVector other)
    {
        // TODO: swap을 복사 후 교환의 무실패 반영 단계로 만드세요.
        static_cast<void>(other);
        return *this;
    }

    void swap(MiniVector &other) throw()
    {
        std::swap(data_, other.data_);
        std::swap(size_, other.size_);
        std::swap(capacity_, other.capacity_);
    }

    std::size_t size() const
    {
        return size_;
    }

    std::size_t capacity() const
    {
        return capacity_;
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
            throw std::out_of_range("MiniVector::at");
        return data_[index];
    }

    const T &at(std::size_t index) const
    {
        if (index >= size_)
            throw std::out_of_range("MiniVector::at");
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

    void push_back(const T &value)
    {
        static_cast<void>(value);
        // TODO: 제자리에서 생성하거나 별칭에 안전한 절차로 처리하세요.
    }

    void reserve(std::size_t requestedCapacity)
    {
        static_cast<void>(requestedCapacity);
        // TODO: 실패하면 부분 생성된 후보를 모두 되돌리세요.
    }

    void clear()
    {
        while (size_ != 0)
        {
            --size_;
            allocator_.destroy(data_ + size_);
        }
    }

private:
    T *data_;
    std::size_t size_;
    std::size_t capacity_;
    std::allocator<T> allocator_;
};

#endif
