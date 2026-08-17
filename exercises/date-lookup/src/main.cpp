#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>

// [Implementation 1] Canonical calendar date
// Date establishes calendar validity and owns a lexicographically sortable canonical form.
class Date
{
public:
    explicit Date(const std::string &text) : text_() { parse(text); }
    const std::string &str() const { return text_; }
    bool operator<(const Date &other) const { return text_ < other.text_; }

private:
    std::string text_;

    static bool isLeapYear(int year)
    {
        return year % 400 == 0 || (year % 4 == 0 && year % 100 != 0);
    }

    void parse(const std::string &text)
    {
        if (text.size() != 10 || text[4] != '-' || text[7] != '-')
            throw std::invalid_argument("invalid date");
        for (std::size_t i = 0; i < text.size(); ++i)
        {
            if (i != 4 && i != 7 && (text[i] < '0' || text[i] > '9'))
                throw std::invalid_argument("invalid date");
        }

        const int year = std::atoi(text.substr(0, 4).c_str());
        const int month = std::atoi(text.substr(5, 2).c_str());
        const int day = std::atoi(text.substr(8, 2).c_str());
        int daysPerMonth[] = {0, 31, 28, 31, 30, 31, 30,
                             31, 31, 30, 31, 30, 31};
        if (isLeapYear(year))
            daysPerMonth[2] = 29;
        if (year < 1 || month < 1 || month > 12 ||
            day < 1 || day > daysPerMonth[month])
        {
            throw std::invalid_argument("invalid date");
        }
        text_ = text;
    }
};

// [Implementation 2] Total finite-number parsing
// Input normalization trims boundaries and accepts only complete finite numbers.
static std::string trim(const std::string &text)
{
    const std::size_t first = text.find_first_not_of(" \t");
    if (first == std::string::npos)
        return "";
    const std::size_t last = text.find_last_not_of(" \t");
    return text.substr(first, last - first + 1);
}

static double parseFiniteNumber(const std::string &text)
{
    char *end = 0;
    errno = 0;
    const double value = std::strtod(text.c_str(), &end);
    const double maximum = std::numeric_limits<double>::max();
    if (errno == ERANGE || end == text.c_str() || *end != '\0' ||
        value != value || value > maximum || value < -maximum)
    {
        throw std::invalid_argument("invalid number");
    }
    return value;
}

// [Implementation 3] Transactional CSV load
// RateBook validates an entire candidate map before committing a new dataset.
class RateBook
{
public:
    void load(const char *path)
    {
        std::ifstream input(path);
        if (!input)
            throw std::runtime_error("cannot open data file");

        std::map<Date, double> candidate;
        std::string line;
        if (!std::getline(input, line) || line != "date,rate")
            throw std::runtime_error("invalid data header");

        while (std::getline(input, line))
        {
            const std::size_t comma = line.find(',');
            if (comma == std::string::npos ||
                line.find(',', comma + 1) != std::string::npos)
            {
                throw std::runtime_error("invalid data row");
            }

            const Date date(trim(line.substr(0, comma)));
            const double rate = parseFiniteNumber(trim(line.substr(comma + 1)));
            if (rate < 0)
                throw std::runtime_error("rate must not be negative");

            const std::pair<std::map<Date, double>::iterator, bool> inserted =
                candidate.insert(std::make_pair(date, rate));
            if (!inserted.second)
                throw std::runtime_error("duplicate date");
        }
        if (candidate.empty())
            throw std::runtime_error("empty dataset");
        rates_.swap(candidate);
    }

    // [Implementation 4] At-or-before rate lookup
    // upper_bound selects the latest rate not newer than the requested date.
    double atOrBefore(const Date &date) const
    {
        std::map<Date, double>::const_iterator found = rates_.upper_bound(date);
        if (found == rates_.begin())
            throw std::out_of_range("no applicable rate");
        --found;
        return found->second;
    }

private:
    std::map<Date, double> rates_;
};

// [Implementation 5] Query and process error boundaries
// Dataset failure terminates the process; malformed query lines remain isolated per request.
int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "usage: date_lookup data.csv\n";
        return 1;
    }

    try
    {
        RateBook book;
        book.load(argv[1]);

        std::string line;
        while (std::getline(std::cin, line))
        {
            try
            {
                const std::size_t separator = line.find('|');
                if (separator == std::string::npos ||
                    line.find('|', separator + 1) != std::string::npos)
                {
                    throw std::invalid_argument("invalid query format");
                }

                const Date date(trim(line.substr(0, separator)));
                const double amount = parseFiniteNumber(trim(line.substr(separator + 1)));
                if (amount < 0 || amount > 1000)
                {
                    std::cout << "error: amount out of range\n";
                    continue;
                }
                const double result = amount * book.atOrBefore(date);
                std::cout << date.str() << " => " << amount << " = "
                          << result << '\n';
            }
            catch (const std::out_of_range &)
            {
                const std::size_t separator = line.find('|');
                std::cout << "error: no rate before "
                          << trim(line.substr(0, separator)) << '\n';
            }
            catch (const std::invalid_argument &error)
            {
                if (std::string(error.what()) == "invalid date")
                    std::cout << "error: invalid date\n";
                else
                    std::cout << "error: invalid input\n";
            }
        }
    }
    catch (const std::exception &error)
    {
        std::cerr << "fatal: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
