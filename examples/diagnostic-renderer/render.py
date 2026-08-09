#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    start: int
    end: int


class Source:
    def __init__(self, name: str, text: str) -> None:
        self.name = name
        self.text = text
        self.data = text.encode("utf-8")
        self.line_starts = [0]
        index = 0
        while index < len(self.data):
            byte = self.data[index]
            if byte == 0x0D and index + 1 < len(self.data) and self.data[index + 1] == 0x0A:
                index += 2
                self.line_starts.append(index)
                continue
            if byte == 0x0A:
                index += 1
                self.line_starts.append(index)
                continue
            index += 1

    def _decode_boundary(self, offset: int) -> str:
        if not 0 <= offset <= len(self.data):
            raise ValueError(f"offset outside source: {offset}")
        try:
            return self.data[:offset].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"offset {offset} is not a UTF-8 boundary") from exc

    def line_index(self, offset: int) -> int:
        self._decode_boundary(offset)
        lo, hi = 0, len(self.line_starts)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid
        return lo

    def line_bounds(self, line_index: int) -> tuple[int, int]:
        start = self.line_starts[line_index]
        end = self.line_starts[line_index + 1] if line_index + 1 < len(self.line_starts) else len(self.data)
        while end > start and self.data[end - 1] in (0x0A, 0x0D):
            end -= 1
        return start, end

    def line_column(self, offset: int) -> tuple[int, int]:
        line = self.line_index(offset)
        start, _ = self.line_bounds(line)
        prefix = self.data[start:offset].decode("utf-8")
        return line + 1, len(prefix) + 1


def render(source: Source, span: Span, code: str, message: str) -> str:
    if not 0 <= span.start <= span.end <= len(source.data):
        raise ValueError("invalid span")
    source._decode_boundary(span.start)
    source._decode_boundary(span.end)
    start_line = source.line_index(span.start)
    end_line = source.line_index(span.end)
    if start_line != end_line:
        raise ValueError("this small example only renders one-line spans")
    line_start, line_end = source.line_bounds(start_line)
    line_text = source.data[line_start:line_end].decode("utf-8")
    prefix = source.data[line_start:span.start].decode("utf-8")
    marked = source.data[span.start:span.end].decode("utf-8")
    line, column = source.line_column(span.start)
    underline = " " * len(prefix.expandtabs(4)) + "^" * max(1, len(marked.expandtabs(4)))
    return f"{source.name}:{line}:{column}: error[{code}]: {message}\n{line_text.expandtabs(4)}\n{underline}"


def demo() -> str:
    text = 'fn main() {\n    print_string("한글🙂");\n}\n'
    source = Source("unicode.mica", text)
    start = source.data.index("🙂".encode("utf-8"))
    return render(source, Span(start, start + len("🙂".encode("utf-8"))), "MICA1001", "demo span")


def self_test() -> None:
    output = demo()
    expected = "unicode.mica:2:21: error[MICA1001]: demo span"
    assert output.splitlines()[0] == expected, output
    assert output.splitlines()[2].endswith("^"), output
    source = Source("x", "🙂")
    try:
        source.line_column(1)
    except ValueError:
        pass
    else:
        raise AssertionError("mid-codepoint byte offset was accepted")
    print("PASS diagnostic renderer")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(demo())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
