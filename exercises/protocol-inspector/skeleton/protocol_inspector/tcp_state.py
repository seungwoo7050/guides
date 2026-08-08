"""TCP 상태 전이 실습의 미완성 구현입니다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import InvalidTransition


class EndpointRole(str, Enum):
    CLIENT = "client"
    SERVER = "server"


class TCPState(str, Enum):
    CLOSED = "CLOSED"
    LISTEN = "LISTEN"
    SYN_SENT = "SYN-SENT"
    SYN_RECEIVED = "SYN-RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT_1 = "FIN-WAIT-1"
    FIN_WAIT_2 = "FIN-WAIT-2"
    CLOSE_WAIT = "CLOSE-WAIT"
    CLOSING = "CLOSING"
    LAST_ACK = "LAST-ACK"
    TIME_WAIT = "TIME-WAIT"


class TCPEvent(str, Enum):
    PASSIVE_OPEN = "passive-open"
    ACTIVE_OPEN = "active-open"
    RECEIVE_SYN = "receive-syn"
    RECEIVE_SYN_ACK = "receive-syn-ack"
    RECEIVE_ACK = "receive-ack"
    APP_CLOSE = "app-close"
    RECEIVE_FIN = "receive-fin"
    RECEIVE_FIN_ACK = "receive-fin-ack"
    RECEIVE_RST = "receive-rst"
    TIMEOUT = "timeout"


@dataclass
class TCPEndpoint:
    role: EndpointRole
    state: TCPState = TCPState.CLOSED

    def apply(self, event: TCPEvent) -> TCPState:
        raise NotImplementedError("현재 상태와 사건으로 다음 상태를 결정하세요")
