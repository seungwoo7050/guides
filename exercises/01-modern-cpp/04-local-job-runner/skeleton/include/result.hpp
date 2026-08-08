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
        // TODO: 실패 상태 접근을 logic_error로 거부한 뒤 성공값을 반환합니다.
        return std::get<0>(storage_);
    }

    [[nodiscard]] const Value& value() const
    {
        // TODO: const Result에서도 같은 잘못된 접근 계약을 적용합니다.
        return std::get<0>(storage_);
    }

    [[nodiscard]] Error& error()
    {
        // TODO: 성공 상태 접근을 logic_error로 거부한 뒤 오류값을 반환합니다.
        return std::get<1>(storage_);
    }

    [[nodiscard]] const Error& error() const
    {
        // TODO: const Result에서도 같은 잘못된 접근 계약을 적용합니다.
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
