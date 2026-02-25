Canonical formatting for agents and contributors
=============================================

Purpose
-------
This file clarifies how agents and humans should refer to files, paths and symbols when writing messages or documentation in this repository.

Rules
-----
- File references: Always use workspace-relative Markdown links when pointing to files or line ranges. Example: [src/config.py](src/config.py#L10).
- Do NOT wrap file paths or links in backticks.
- Symbol names (classes, functions, variables) may be wrapped in backticks when mentioned inline, e.g. `MyClass`, `handle_click()`.
- When both a file and a symbol are referenced, prefer a file link for the location and backticks for the symbol: see [src/config.py](src/config.py#L10) — `MyClass`.
- Examples:
  - File only: [README.md](README.md)
  - File + lines: [tests/test_html_parser.py](tests/test_html_parser.py#L12-L20)
  - Symbol in prose: Use `parse_html()` to extract events.

Why
---
These rules match the repository's documentation conventions and avoid ambiguous or conflicting formatting guidance.

If you maintain agent or assistant instructions in this repo, update them to reference this file to avoid conflicts.
