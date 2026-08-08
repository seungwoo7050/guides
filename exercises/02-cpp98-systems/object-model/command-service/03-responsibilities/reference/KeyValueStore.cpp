#include "KeyValueStore.hpp"

KeyValueStore::KeyValueStore(std::size_t capacity)
    : capacity_(capacity), data_()
{
}

bool KeyValueStore::put(
    const std::string &key,
    const std::string &value)
{
    const bool isNewKey = data_.find(key) == data_.end();
    if (isNewKey && data_.size() >= capacity_)
        return false;

    data_[key] = value;
    return true;
}

bool KeyValueStore::get(
    const std::string &key,
    std::string &value) const
{
    const std::map<std::string, std::string>::const_iterator found
        = data_.find(key);
    if (found == data_.end())
        return false;

    value = found->second;
    return true;
}

bool KeyValueStore::erase(const std::string &key)
{
    return data_.erase(key) != 0;
}

std::size_t KeyValueStore::size() const
{
    return data_.size();
}
