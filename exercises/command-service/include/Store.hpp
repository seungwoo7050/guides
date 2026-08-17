#ifndef COMMAND_SERVICE_STORE_HPP
#define COMMAND_SERVICE_STORE_HPP

#include "TextBuffer.hpp"

#include <cstddef>
#include <map>
#include <string>
#include <vector>

struct StoreEntry
{
    std::string key;
    std::string value;

    StoreEntry(const std::string &entryKey, const std::string &entryValue)
        : key(entryKey), value(entryValue)
    {
    }
};

// [Implementation 3] Bounded store ownership
// Store owns the bounded ordered key/value state and exposes domain operations only.
class Store
{
public:
    explicit Store(std::size_t capacity);

    void putNew(const std::string &key, const std::string &value);
    bool get(const std::string &key, std::string &value) const;
    bool erase(const std::string &key);
    std::size_t size() const;
    std::size_t capacity() const;
    std::vector<StoreEntry> entries() const;

private:
    std::size_t capacity_;
    std::map<std::string, TextBuffer> data_;
};

#endif
