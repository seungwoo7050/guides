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
    typedef T value_type;
    typedef T *iterator;
    typedef const T *const_iterator;

    MiniVector()
        : data_(0), size_(0), capacity_(0), allocator_()
    {
    }

    MiniVector(const MiniVector &other)
        : data_(0), size_(0), capacity_(0), allocator_()
    {
        copyFrom(other);
    }

    ~MiniVector()
    {
        destroyElements();
        if (data_ != 0)
            allocator_.deallocate(data_, capacity_);
    }

    MiniVector &operator=(MiniVector other)
    {
        swap(other);
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

    bool empty() const
    {
        return size_ == 0;
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
        if (size_ < capacity_)
        {
            allocator_.construct(data_ + size_, value);
            ++size_;
            return;
        }

        const std::size_t nextCapacity = growthCapacity();
        T *candidate = allocator_.allocate(nextCapacity);
        std::size_t built = 0;

        try
        {
            for (; built < size_; ++built)
                allocator_.construct(candidate + built, data_[built]);

            // value가 data_ 안의 원소를 참조해도 기존 저장소는 아직 살아 있습니다.
            allocator_.construct(candidate + built, value);
            ++built;
        }
        catch (...)
        {
            destroyBuilt(candidate, built);
            allocator_.deallocate(candidate, nextCapacity);
            throw;
        }

        replaceStorage(candidate, built, nextCapacity);
    }

    void reserve(std::size_t requestedCapacity)
    {
        if (requestedCapacity <= capacity_)
            return;
        if (requestedCapacity > allocator_.max_size())
            throw std::length_error("MiniVector::reserve");

        T *candidate = allocator_.allocate(requestedCapacity);
        std::size_t built = 0;

        try
        {
            for (; built < size_; ++built)
                allocator_.construct(candidate + built, data_[built]);
        }
        catch (...)
        {
            destroyBuilt(candidate, built);
            allocator_.deallocate(candidate, requestedCapacity);
            throw;
        }

        replaceStorage(candidate, built, requestedCapacity);
    }

    void clear()
    {
        destroyElements();
        size_ = 0;
    }

private:
    T *data_;
    std::size_t size_;
    std::size_t capacity_;
    std::allocator<T> allocator_;

    std::size_t growthCapacity() const
    {
        if (capacity_ == 0)
            return 1;
        if (capacity_ > allocator_.max_size() / 2)
            throw std::length_error("MiniVector 용량이 표현 범위를 벗어났습니다");
        return capacity_ * 2;
    }

    void destroyBuilt(T *memory, std::size_t count)
    {
        while (count != 0)
        {
            --count;
            allocator_.destroy(memory + count);
        }
    }

    void destroyElements()
    {
        destroyBuilt(data_, size_);
    }

    void replaceStorage(
        T *candidate,
        std::size_t candidateSize,
        std::size_t candidateCapacity)
    {
        destroyElements();
        if (data_ != 0)
            allocator_.deallocate(data_, capacity_);

        data_ = candidate;
        size_ = candidateSize;
        capacity_ = candidateCapacity;
    }

    void copyFrom(const MiniVector &other)
    {
        if (other.size_ == 0)
            return;

        T *candidate = allocator_.allocate(other.size_);
        std::size_t built = 0;

        try
        {
            for (; built < other.size_; ++built)
                allocator_.construct(candidate + built, other.data_[built]);
        }
        catch (...)
        {
            destroyBuilt(candidate, built);
            allocator_.deallocate(candidate, other.size_);
            throw;
        }

        data_ = candidate;
        size_ = other.size_;
        capacity_ = other.size_;
    }
};

#endif
