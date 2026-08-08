#ifndef KEYVALUESTORE_HPP
#define KEYVALUESTORE_HPP

#include <cstddef>
#include <map>
#include <string>

class KeyValueStore
{
public:
    explicit KeyValueStore(std::size_t capacity);

    bool put(const std::string &key, const std::string &value);
    bool get(const std::string &key, std::string &value) const;
    bool erase(const std::string &key);
    std::size_t size() const;

private:
    std::size_t capacity_;
    std::map<std::string, std::string> data_;
};

#endif
