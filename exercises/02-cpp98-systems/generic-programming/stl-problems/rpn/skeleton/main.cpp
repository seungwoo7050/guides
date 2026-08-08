#include <iostream>

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "사용법: rpn 수식\n";
        return 1;
    }

    static_cast<void>(argv);
    std::cerr << "오류: 아직 구현되지 않았습니다\n";

    // TODO: 식을 토큰으로 나누고 std::stack으로 계산하세요.
    return 1;
}
