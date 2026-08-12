#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>

// [Implementation 1] Date가 달력 유효성을 생성 시 확립하고 정렬 가능한 canonical YYYY-MM-DD 표현을 소유합니다.
class Date
{
public:
    Date() : text_() {}

    explicit Date(const std::string &text)
        : text_()
    {
        parse(text);
    }

    const std::string &str() const
    {
        return text_;
    }

    bool operator<(const Date &other) const
    {
        return text_ < other.text_;
    }

private:
    std::string text_;

    static bool isLeapYear(int year)
    {
        return year % 400 == 0
            || (year % 4 == 0 && year % 100 != 0);
    }

    void parse(const std::string &text)
    {
        if (text.size() != 10 || text[4] != '-' || text[7] != '-')
            throw std::invalid_argument("날짜가 올바르지 않습니다");

        for (std::size_t i = 0; i < text.size(); ++i)
        {
            if (i != 4 && i != 7
                && (text[i] < '0' || text[i] > '9'))
            {
                throw std::invalid_argument("날짜가 올바르지 않습니다");
            }
        }

        const int year = std::atoi(text.substr(0, 4).c_str());
        const int month = std::atoi(text.substr(5, 2).c_str());
        const int day = std::atoi(text.substr(8, 2).c_str());

        int daysPerMonth[] = {
            0, 31, 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31
        };
        if (isLeapYear(year))
            daysPerMonth[2] = 29;

        if (year < 1 || month < 1 || month > 12
            || day < 1 || day > daysPerMonth[month])
        {
            throw std::invalid_argument("날짜가 올바르지 않습니다");
        }

        text_ = text;
    }
};

// [Implementation 2] 경계 공백을 제거한 뒤 문자열 전체가 유한한 수인지 확인하는 입력 정규화 계층을 만듭니다.
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

    if (errno == ERANGE || end == text.c_str() || *end != '\0'
        || value != value || value > maximum || value < -maximum)
    {
        throw std::invalid_argument("숫자가 올바르지 않습니다");
    }
    return value;
}

// [Implementation 3] RateBook은 CSV 전체를 candidate map으로 검증한 뒤 swap하여 실패한 load가 기존 상태를 바꾸지 않게 합니다.
class RateBook
{
public:
    void load(const char *path)
    {
        std::ifstream input(path);
        if (!input)
            throw std::runtime_error("데이터 파일을 열 수 없습니다");

        std::map<Date, double> candidate;
        std::string line;
        if (!std::getline(input, line) || line != "date,rate")
            throw std::runtime_error("데이터 머리글이 올바르지 않습니다");

        while (std::getline(input, line))
        {
            const std::size_t comma = line.find(',');
            if (comma == std::string::npos
                || line.find(',', comma + 1) != std::string::npos)
            {
                throw std::runtime_error("데이터 행이 올바르지 않습니다");
            }

            const Date date(trim(line.substr(0, comma)));
            const double rate = parseFiniteNumber(
                trim(line.substr(comma + 1)));
            if (rate < 0)
                throw std::runtime_error("환율은 음수일 수 없습니다");

            const std::pair<std::map<Date, double>::iterator, bool> inserted
                = candidate.insert(std::make_pair(date, rate));
            if (!inserted.second)
                throw std::runtime_error("날짜가 중복되었습니다");
        }

        if (candidate.empty())
            throw std::runtime_error("데이터가 비어 있습니다");

        rates_.swap(candidate);
    }

    // [Implementation 4] upper_bound의 직전 원소를 선택하고 가장 이른 날짜보다 앞선 조회는 명시적으로 거부합니다.
    double atOrBefore(const Date &date) const
    {
        std::map<Date, double>::const_iterator found
            = rates_.upper_bound(date);
        if (found == rates_.begin())
            throw std::out_of_range("적용할 환율이 없습니다");
        --found;
        return found->second;
    }

private:
    std::map<Date, double> rates_;
};

// [Implementation 5] 데이터 파일 실패는 process 경계에서, 개별 조회 실패는 다음 입력을 계속 받을 수 있는 결과로 번역합니다.
int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "사용법: date_lookup data.csv\n";
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
                if (separator == std::string::npos
                    || line.find('|', separator + 1) != std::string::npos)
                {
                    throw std::invalid_argument("입력 형식이 올바르지 않습니다");
                }

                const Date date(trim(line.substr(0, separator)));
                const double amount = parseFiniteNumber(
                    trim(line.substr(separator + 1)));

                if (amount < 0 || amount > 1000)
                {
                    std::cout << "오류: 금액이 허용 범위를 벗어났습니다\n";
                    continue;
                }

                const double result = amount * book.atOrBefore(date);
                std::cout << date.str() << " => " << amount
                          << " = " << result << '\n';
            }
            catch (const std::out_of_range &)
            {
                const std::size_t separator = line.find('|');
                const std::string dateText = trim(
                    line.substr(0, separator));
                std::cout << "오류: " << dateText << " 이전의 환율이 없습니다\n";
            }
            catch (const std::invalid_argument &error)
            {
                if (std::string(error.what()) == "날짜가 올바르지 않습니다")
                    std::cout << "오류: 날짜가 올바르지 않습니다\n";
                else
                    std::cout << "오류: 입력이 올바르지 않습니다\n";
            }
        }
    }
    catch (const std::exception &error)
    {
        std::cerr << "치명적 오류: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
