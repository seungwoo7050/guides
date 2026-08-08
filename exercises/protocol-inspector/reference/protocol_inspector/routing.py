"""IPv4 라우팅 테이블의 longest-prefix match를 구현합니다."""

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
        if not interface:
            raise ValueError("인터페이스 이름은 비어 있을 수 없습니다")
        if metric < 0:
            raise ValueError("metric은 음수일 수 없습니다")
        return cls(
            network=ipaddress.IPv4Network(network, strict=False),
            interface=interface,
            next_hop=ipaddress.IPv4Address(next_hop) if next_hop else None,
            metric=metric,
        )


class RoutingTable:
    """동일 prefix에서는 낮은 metric과 먼저 추가된 경로를 우선합니다."""

    def __init__(self, routes: list[Route] | None = None) -> None:
        self._routes: list[Route] = list(routes or [])

    def add(self, route: Route) -> None:
        self._routes.append(route)

    def lookup(self, destination: str | ipaddress.IPv4Address) -> Route | None:
        address = ipaddress.IPv4Address(destination)
        candidates = [
            (route.network.prefixlen, -route.metric, -index, route)
            for index, route in enumerate(self._routes)
            if address in route.network
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[:3])[3]

    def routes(self) -> tuple[Route, ...]:
        return tuple(self._routes)
