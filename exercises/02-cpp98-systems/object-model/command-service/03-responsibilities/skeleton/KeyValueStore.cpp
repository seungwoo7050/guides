#include "KeyValueStore.hpp"

KeyValueStore::KeyValueStore(std::size_t capacity)
    : capacity_(capacity), data_()
{
}

bool KeyValueStore::put(
    const std::string &key,
    const std::string &value)
{
    static_cast<void>(key);
    static_cast<void>(value);
    static_cast<void>(capacity_);
    // TODO: 기존 키의 갱신은 허용하면서 capacity_ 제한을 지키세요.
    return false;
}

bool KeyValueStore::get(
    const std::string &key,
    std::string &value) const
{
    static_cast<void>(key);
    static_cast<void>(value);
    // TODO: data_를 노출하지 않고 저장된 값을 반환하세요.
    return false;
}

bool KeyValueStore::erase(const std::string &key)
{
    static_cast<void>(key);
    // TODO: 키를 지우고 기존에 있었는지 반환하세요.
    return false;
}

std::size_t KeyValueStore::size() const
{
    return data_.size();
}
