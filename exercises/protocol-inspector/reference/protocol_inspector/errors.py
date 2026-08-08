"""프로토콜 실습에서 사용하는 예외 형식입니다."""


class PacketFormatError(ValueError):
    """바이트열이 선언한 프로토콜 형식을 만족하지 않을 때 발생합니다."""


class InvalidTransition(ValueError):
    """현재 TCP 상태에서 허용되지 않은 사건이 들어올 때 발생합니다."""
