#include <algorithm>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <stdexcept>
#include <vector>

// [Implementation 1] Stable record model
// Each record retains both its sort key and original input position.
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

// [Implementation 2] Total argument validation
// Every argument must be a complete non-negative int token.
static int parseNonNegativeInteger(const char *text)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        value < 0 || value > INT_MAX)
    {
        throw std::invalid_argument("expected a non-negative integer");
    }
    return static_cast<int>(value);
}

static void printValues(const char *label, const std::vector<Record> &records)
{
    std::cout << label;
    for (std::size_t index = 0; index < records.size(); ++index)
        std::cout << ' ' << records[index].value;
    std::cout << '\n';
}

// [Implementation 3] Record materialization
// Validated arguments materialize records with their original order metadata.
int main(int argc, char **argv)
{
    if (argc < 2)
    {
        std::cerr << "usage: stable_sorter non-negative-integer...\n";
        return 1;
    }

    try
    {
        std::vector<Record> records;
        records.reserve(static_cast<std::size_t>(argc - 1));
        for (int index = 1; index < argc; ++index)
        {
            records.push_back(Record(parseNonNegativeInteger(argv[index]),
                                     static_cast<std::size_t>(index - 1)));
        }
        printValues("before:", records);

        // [Implementation 4] Stable sort and measurement
        // stable_sort preserves equal-key input order and timing excludes parsing and output.
        const std::clock_t startedAt = std::clock();
        std::stable_sort(records.begin(), records.end(), RecordLess());
        const std::clock_t finishedAt = std::clock();

        printValues("after:", records);
        std::cerr << "sorted " << records.size() << " values in "
                  << (1000000.0 * (finishedAt - startedAt) / CLOCKS_PER_SEC)
                  << "us\n";
    }
    catch (const std::exception &error)
    {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
