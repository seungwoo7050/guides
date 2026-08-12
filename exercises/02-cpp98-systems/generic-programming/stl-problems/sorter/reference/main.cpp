#include <algorithm>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <stdexcept>
#include <vector>

// [Implementation 1] 정렬 key와 원래 입력 위치를 함께 보존하는 record 및 stable 비교 계약을 정의합니다.
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

// [Implementation 2] 각 argument 전체를 소비하고 음이 아닌 int 범위만 입력 모델로 받아들입니다.
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

// [Implementation 3] 검증된 argument를 입력 순서를 가진 Record 목록으로 materialize합니다.
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

        // [Implementation 4] stable_sort의 결과와 측정 구간을 분리해 동일 key의 입력 순서 보존을 관찰합니다.
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
