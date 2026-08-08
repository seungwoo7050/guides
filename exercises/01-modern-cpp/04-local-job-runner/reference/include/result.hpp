#ifndef GUIDE_MODERN_RESULT_HPP
#define GUIDE_MODERN_RESULT_HPP

#include <cstddef>
#include <stdexcept>
#include <utility>
#include <variant>

namespace guide
{
template <typename Value, typename Error>
class Result
{
public:
    [[nodiscard]] static Result success(Value value)
    {
        return Result{std::in_place_index<0>, std::move(value)};
    }

    [[nodiscard]] static Result failure(Error error)
    {
        return Result{std::in_place_index<1>, std::move(error)};
    }

    [[nodiscard]] bool has_value() const noexcept
    {
        return storage_.index() == 0;
    }

    explicit operator bool() const noexcept { return has_value(); }

    [[nodiscard]] Value& value()
    {
        if (!has_value())
            throw std::logic_error("Result does not contain a value");
        return std::get<0>(storage_);
    }

    [[nodiscard]] const Value& value() const
    {
        if (!has_value())
            throw std::logic_error("Result does not contain a value");
        return std::get<0>(storage_);
    }

    [[nodiscard]] Error& error()
    {
        if (has_value())
            throw std::logic_error("Result does not contain an error");
        return std::get<1>(storage_);
    }

    [[nodiscard]] const Error& error() const
    {
        if (has_value())
            throw std::logic_error("Result does not contain an error");
        return std::get<1>(storage_);
    }

private:
    template <std::size_t Index, typename Item>
    Result(std::in_place_index_t<Index> index, Item&& item)
        : storage_(index, std::forward<Item>(item))
    {}

    std::variant<Value, Error> storage_;
};
} // namespace guide

#endif
