#include <iostream>

int main(int argc, char **argv)
{
    static_cast<void>(argv);
    if (argc != 5)
    {
        std::cerr
            << "사용법: integrated_http_server "
            << "포트 설정-파일 CGI-실행-파일 CGI-제한-시간-ms\n";
        return 2;
    }

    std::cerr
        << "요청 파서, 라우터, 이벤트 루프와 CGI 실행기를 "
        << "하나의 서버 흐름으로 연결해 주세요\n";
    return 78;
}
