#include <cstdlib>
#include <iostream>
#include <vector>

static void printValues(
    const char *label,
    const std::vector<int> &values)
{
    std::cout << label;
    for (std::size_t index = 0; index < values.size(); ++index)
        std::cout << ' ' << values[index];
    std::cout << '\n';
}

int main(int argc, char **argv)
{
    if (argc < 2)
    {
        std::cerr << "사용법: sorter 음이-아닌-정수...\n";
        return 1;
    }

    std::vector<int> values;
    for (int index = 1; index < argc; ++index)
        values.push_back(std::atoi(argv[index]));

    printValues("Before:", values);

    // TODO:
    // 1. 모든 인자를 엄격하게 파싱하고 잘못된 값이나 음수를 거부합니다.
    // 2. 같은 값을 가진 레코드의 입력 순서를 보존하도록 정렬합니다.
    // 3. 정렬 구간만 별도로 측정하고 결과와 진단 출력을 분리합니다.

    printValues("After:", values);
    return 0;
}
