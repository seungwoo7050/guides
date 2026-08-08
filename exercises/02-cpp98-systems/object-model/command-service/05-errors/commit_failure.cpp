#include <cassert>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

namespace
{
typedef std::map<std::string, std::string> Config;

void validate(const Config &config)
{
    if (config.find("bad") != config.end())
        throw std::runtime_error("키가 올바르지 않습니다");
}

void applyBad(Config &target, const Config &patch)
{
    target.insert(patch.begin(), patch.end());
    validate(target);
}

void applyGood(Config &target, const Config &patch)
{
    Config candidate(target);
    candidate.insert(patch.begin(), patch.end());
    validate(candidate);
    target.swap(candidate);
}
}

int main()
{
    Config patch;
    patch["bad"] = "x";

    Config badTarget;
    badTarget["stable"] = "yes";
    try
    {
        applyBad(badTarget, patch);
    }
    catch (const std::exception &)
    {
    }
    assert(badTarget.find("bad") != badTarget.end());

    Config goodTarget;
    goodTarget["stable"] = "yes";
    try
    {
        applyGood(goodTarget, patch);
    }
    catch (const std::exception &)
    {
    }
    assert(goodTarget.find("bad") == goodTarget.end());
    assert(goodTarget["stable"] == "yes");

    std::cout
        << "잘못된 갱신은 중간 상태를 노출했고, "
        << "준비 후 반영 방식은 대상 값을 보존했습니다\n";
}
