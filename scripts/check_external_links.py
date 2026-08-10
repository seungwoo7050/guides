#!/usr/bin/env python3
"""Check deduplicated external Markdown links without affecting local verify."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag
from urllib.request import Request, build_opener
import re


INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")
AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
USER_AGENT = "embedded-systems-guide-link-check/1.0 (+https://github.com/seungwoo7050/guides)"


def markdown_urls(root: Path) -> list[str]:
    urls: set[str] = set()
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        candidates = [first or second for first, second in INLINE_LINK.findall(text)]
        candidates.extend(AUTOLINK.findall(text))
        for candidate in candidates:
            if candidate.startswith(("http://", "https://")):
                clean, _ = urldefrag(candidate)
                urls.add(clean)
    return sorted(urls)


def request_url(url: str, timeout: float) -> dict[str, Any]:
    opener = build_opener()  # Redirect handlers are enabled by default.
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    request = Request(url, headers=headers, method="HEAD")
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as error:
        if error.code not in {405, 501}:
            return {"url": url, "status": "HTTP_ERROR", "http_status": error.code, "detail": str(error)}
        # Some sites do not implement HEAD.  A bounded range GET still avoids a
        # full body while exercising redirects and access policy.
        request = Request(url, headers={**headers, "Range": "bytes=0-0"}, method="GET")
        try:
            response = opener.open(request, timeout=timeout)
        except HTTPError as retry_error:
            return {"url": url, "status": "HTTP_ERROR", "http_status": retry_error.code, "detail": str(retry_error)}
        except (TimeoutError, socket.timeout) as retry_error:
            return {"url": url, "status": "TIMEOUT", "detail": str(retry_error)}
        except URLError as retry_error:
            return {"url": url, "status": "NETWORK_ERROR", "detail": str(retry_error.reason)}
    except (TimeoutError, socket.timeout) as error:
        return {"url": url, "status": "TIMEOUT", "detail": str(error)}
    except URLError as error:
        return {"url": url, "status": "NETWORK_ERROR", "detail": str(error.reason)}
    except ValueError as error:
        return {"url": url, "status": "INVALID_URL", "detail": str(error)}
    try:
        status = response.getcode()
        final_url = response.geturl()
        response.close()
    except OSError as error:
        return {"url": url, "status": "NETWORK_ERROR", "detail": str(error)}
    if status is None or not 200 <= status < 400:
        return {"url": url, "status": "HTTP_ERROR", "http_status": status, "final_url": final_url}
    return {"url": url, "status": "OK", "http_status": status, "final_url": final_url}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    root = args.root.resolve()
    try:
        urls = markdown_urls(root)
    except (OSError, UnicodeError) as error:
        print(f"ERROR: cannot collect Markdown URLs: {error}", file=sys.stderr)
        return 2
    results = [request_url(url, args.timeout) for url in urls]
    failures = [result for result in results if result["status"] != "OK"]
    report = {
        "status": "PASS" if not failures else "FAIL",
        "checked": len(results),
        "failed": len(failures),
        "results": results,
    }
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for result in results:
            suffix = f" -> {result.get('final_url')}" if result.get("final_url") != result["url"] else ""
            detail = f" ({result.get('detail')})" if result.get("detail") else ""
            print(f"{result['status']} {result['url']}{suffix}{detail}")
        print(f"EXTERNAL LINKS {report['status']} checked={report['checked']} failed={report['failed']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
