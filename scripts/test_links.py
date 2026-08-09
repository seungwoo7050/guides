#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from check_links import check_repository


class LinkCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="cloud-link-check-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str | bytes = "") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def codes(self) -> list[str]:
        return [item.code for item in check_repository(self.root).diagnostics]

    def test_valid_inline_image_reference_and_heading_fragments(self) -> None:
        self.write(
            "README.md",
            """# Home

[inline](docs/target%20file.md)
![image](assets/pixel.png)
[fragment](docs/target%20file.md#intro)
[duplicate](docs/target%20file.md#repeat-1)
[self](#home)
[full reference][guide]
[guide][]
[guide]
![reference image][pixel]
[external](https://example.invalid/manual)
[mail](mailto:owner@example.invalid)

[guide]: <docs/target%20file.md#intro> "Guide"
[pixel]: assets/pixel.png
""",
        )
        self.write("docs/target file.md", "# Intro\n\n## Repeat\n\n## Repeat\n")
        self.write("assets/pixel.png", b"not-a-real-image")
        self.write(".git/broken.md", "[broken](missing.md)\n")
        self.write(".guide/broken.md", "[broken](missing.md)\n")
        self.write(".workspace/broken.md", "[broken](missing.md)\n")

        result = check_repository(self.root)

        self.assertTrue(result.ok, result.diagnostics)
        self.assertEqual(2, result.markdown_files)
        self.assertEqual(2, result.external_targets_excluded)
        self.assertGreaterEqual(result.local_targets_checked, 7)

    def test_missing_local_target(self) -> None:
        self.write("README.md", "[missing](docs/nope.md)\n")
        self.assertEqual(["E_LINK_MISSING"], self.codes())

    def test_missing_heading_fragment(self) -> None:
        self.write("README.md", "[section](guide.md#not-a-heading)\n")
        self.write("guide.md", "# Existing heading\n")
        self.assertEqual(["E_LINK_FRAGMENT"], self.codes())

    def test_missing_reference_definition(self) -> None:
        self.write("README.md", "[label][undefined]\n")
        self.assertEqual(["E_LINK_REFERENCE"], self.codes())

    def test_malformed_reference_definition(self) -> None:
        self.write("README.md", "[empty]:\n")
        self.assertEqual(["E_LINK_REFERENCE"], self.codes())

    def test_absolute_and_file_urls_are_rejected(self) -> None:
        for target in ("/etc/passwd", "file:///etc/passwd"):
            with self.subTest(target=target):
                self.write("README.md", f"[unsafe]({target})\n")
                self.assertEqual(["E_LINK_ESCAPE"], self.codes())

    def test_nul_and_backslash_are_rejected_after_percent_decoding(self) -> None:
        for target in ("docs%00/guide.md", "docs%5Cguide.md", "docs%ZZguide.md"):
            with self.subTest(target=target):
                self.write("README.md", f"[unsafe]({target})\n")
                self.assertEqual(["E_LINK_ESCAPE"], self.codes())

    def test_plain_and_percent_encoded_traversal_are_rejected(self) -> None:
        for target in ("../outside.md", "%2e%2e/outside.md"):
            with self.subTest(target=target):
                self.write("README.md", f"[escape]({target})\n")
                self.assertEqual(["E_LINK_ESCAPE"], self.codes())

    def test_symbolic_link_component_is_rejected(self) -> None:
        outside = Path(self.temporary.name + "-outside")
        outside.mkdir()
        self.addCleanup(lambda: outside.rmdir())
        (outside / "guide.md").write_text("# Outside\n", encoding="utf-8")
        self.addCleanup(lambda: (outside / "guide.md").unlink())
        os.symlink(outside, self.root / "linked")
        self.write("README.md", "[linked](linked/guide.md)\n")
        self.assertEqual(["E_LINK_SYMLINK"], self.codes())

    def test_links_in_code_and_comments_are_ignored(self) -> None:
        self.write(
            "README.md",
            """# Examples

`[inline code](missing.md)`

```md
[fenced](missing.md)
```

<!-- [comment](missing.md) -->
""",
        )
        self.assertEqual([], self.codes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
