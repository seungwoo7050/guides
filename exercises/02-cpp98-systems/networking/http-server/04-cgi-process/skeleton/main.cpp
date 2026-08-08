#include <cstdlib>
#include <iostream>

int main(int argc, char **argv)
{
    if (argc != 4)
    {
        std::cerr << "사용법: cgi_runner 실행-파일 입력 제한-시간-ms\n";
        return 2;
    }

    static_cast<void>(argv);

    // TODO:
    // 1. 자식 프로세스의 표준 입력과 표준 출력에 별도 파이프를 만드세요.
    // 2. `fork` 뒤 자식 쪽 파이프 끝을 `dup2`로 연결하고 요청한 프로그램을 `execve`로 실행하세요.
    // 3. 두 프로세스에서 사용하지 않는 파이프 끝을 모두 닫으세요.
    // 4. 분할 입출력은 논블로킹 poll로 처리하세요.
    // 5. 제한 시간과 출력 크기 상한을 적용하세요.
    // 6. 성공과 실패 경로에서 자식 프로세스를 모두 회수하세요.

    std::cerr << "cgi_runner: 구현이 필요합니다\n";
    return 1;
}
