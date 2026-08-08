"""IPv4 longest-prefix match 실습의 미완성 구현입니다."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress


@dataclass(frozen=True)
class Route:
    network: ipaddress.IPv4Network
    interface: str
    next_hop: ipaddress.IPv4Address | None = None
    metric: int = 0

    @classmethod
    def from_strings(
        cls,
        network: str,
        interface: str,
        *,
        next_hop: str | None = None,
        metric: int = 0,
    ) -> "Route":
        raise NotImplementedError("입력을 IPv4Network와 IPv4Address로 검증하세요")


class RoutingTable:
    """가장 긴 prefix를 우선하는 조회를 완성합니다."""

    def __init__(self, routes: list[Route] | None = None) -> None:
        self._routes: list[Route] = list(routes or [])

    def add(self, route: Route) -> None:
        self._routes.append(route)

    def lookup(self, destination: str | ipaddress.IPv4Address) -> Route | None:
        raise NotImplementedError("prefix 길이, metric, 삽입 순서로 후보를 비교하세요")

    def routes(self) -> tuple[Route, ...]:
        return tuple(self._routes)
