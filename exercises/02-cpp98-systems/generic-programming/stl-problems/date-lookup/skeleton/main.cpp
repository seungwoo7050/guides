#include <iostream>
#include <string>

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "사용법: date_lookup data.csv\n";
        return 1;
    }

    static_cast<void>(argv);
    std::string line;
    while (std::getline(std::cin, line))
    {
        static_cast<void>(line);
        std::cout << "오류: 아직 구현되지 않았습니다\n";
    }

    // TODO: Date, 엄격한 파싱, RateBook과 map::upper_bound를 구현하세요.
    return 0;
}
