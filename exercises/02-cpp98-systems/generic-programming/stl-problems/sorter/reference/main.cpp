#include <algorithm>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <stdexcept>
#include <vector>

struct Record
{
    int value;
    std::size_t inputOrder;

    Record(int recordValue, std::size_t order)
        : value(recordValue), inputOrder(order)
    {
    }
};

struct RecordLess
{
    bool operator()(const Record &left, const Record &right) const
    {
        return left.value < right.value;
    }
};

static int parseNonNegativeInteger(const char *text)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text, &end, 10);

    if (errno != 0 || end == text || *end != '\0'
        || value < 0 || value > INT_MAX)
    {
        throw std::invalid_argument("음이 아닌 정수만 입력할 수 있습니다");
    }

    return static_cast<int>(value);
}

static void printValues(
    const char *label,
    const std::vector<Record> &records)
{
    std::cout << label;
    for (std::size_t index = 0; index < records.size(); ++index)
        std::cout << ' ' << records[index].value;
    std::cout << '\n';
}

int main(int argc, char **argv)
{
    if (argc < 2)
    {
        std::cerr << "사용법: sorter 음이-아닌-정수...\n";
        return 1;
    }

    try
    {
        std::vector<Record> records;
        records.reserve(static_cast<std::size_t>(argc - 1));
        for (int index = 1; index < argc; ++index)
        {
            records.push_back(Record(
                parseNonNegativeInteger(argv[index]),
                static_cast<std::size_t>(index - 1)));
        }

        printValues("정렬 전:", records);

        const std::clock_t startedAt = std::clock();
        std::stable_sort(records.begin(), records.end(), RecordLess());
        const std::clock_t finishedAt = std::clock();

        printValues("정렬 후:", records);
        std::cerr << records.size() << "개 값을 정렬했습니다: "
                  << (1000000.0 * (finishedAt - startedAt) / CLOCKS_PER_SEC)
                  << "us\n";
    }
    catch (const std::exception &error)
    {
        std::cerr << "오류: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
