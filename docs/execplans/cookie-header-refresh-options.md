---
title: "Cookie header refresh: automation options"
author: "GitHub Copilot (GPT-5.2)"
date: "2026-02-26"
status: "draft"
estimated_effort: "3–10h (depending on option)"
---

# Cookie header refresh: automation options

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective must be kept up to date as work proceeds.

There is no PLANS.md in this repository at the time of writing; follow the conventions described in skills-repo/skills/planning/SKILL.md.

## Purpose / Big Picture

This repository can run fully automatically on GitHub Actions only if it has a valid Lectio session cookie stored in the GitHub Secret `LECTIO_COOKIE_HEADER`. MitID login is not automated in this repo (and should not be), which means the cookie will eventually expire.

This ExecPlan provides one practical option to keep the cookie current:

1) A helper command that extracts a Cookie header value from something you copy in DevTools, and updates GitHub Secrets (preferably without ever printing the cookie).

The success criteria are:

- You can keep the GitHub Actions workflow in .github/workflows/update-calendar.yml running long-term.
- When the cookie expires, recovery takes minutes and is well documented.
- Private schedule data and cookie values are never printed to logs or committed.

## Non-goals / constraints (important)

- We do not attempt to bypass MitID or automate 2FA.
- We do not attempt to “steal” cookies from your browser profile files (Chrome/Edge encrypt cookies at rest; doing this reliably is brittle and security-sensitive).
- We do not commit cookies to git. Cookie values must stay local, or in GitHub Secrets.
- In CI logs, we only print non-sensitive diagnostics (already implemented via `--debug-fetch`).

## Feasibility evaluation (what will and will not work)

We will not scrape cookies from your normal browser profile (Chrome/Edge) because cookies are encrypted at rest and formats change over time. Doing this reliably would be brittle and security-sensitive.

The approach that remains robust is: you log into Lectio normally, copy request headers (or “copy as cURL”) from DevTools, and the helper extracts/normalizes the `Cookie:` value and updates GitHub Secrets.

## Progress

- [ ] (2026-02-26) Implement the cookie helper command (Option C).
- [ ] (2026-02-26) Add a local helper command that can output a correctly formatted cookie header string.
- [ ] (2026-02-26) Add `gh secret set` integration for one-command secret updates.
- [ ] (2026-02-26) Document the workflow in README.md.
- [ ] (2026-02-26) Validate end-to-end: cookie expired -> helper -> secrets updated -> workflow green.

## Option C: Minimal “easy copy/paste” helper (no new browser automation)

Implement a helper program that guides you through copying the cookie from Developer Tools and updates GitHub Secrets with minimal friction.

The UX goal is:

- Happy path: copy something from DevTools, run one command, secret updated, cookie never printed.
- Fallback: if `gh` is missing/not logged in, print the normalized cookie header value so you can paste it into GitHub Secrets.

### Proposed flow

1) You open Lectio in Chrome/Edge and login normally.

2) In DevTools → Network, you click the request for SkemaAvanceret.aspx.

3) You copy either:

    - the Request Header `Cookie: ...` line, or
    - “Copy request headers” text.

4) You run a local command that prompts you to paste the text. The helper:

    - extracts the cookie value
    - normalizes it (removes leading `Cookie:`, strips quotes)
    - validates it looks non-empty and contains `=` and `;` separators
    - updates GitHub Secrets via `gh secret set` by default
    - prints the cookie only if you explicitly request `--print-cookie`, or if automatic secret update is not possible

5) “No paste” improvement (clipboard)

On Windows we can support a clipboard-first flow:

- You copy the headers/cURL from DevTools.
- You run the helper with `--from-clipboard`.
- It reads the clipboard and proceeds.

Implementation note: prefer the Python standard library `tkinter` for clipboard access (no new dependency). If clipboard access fails, fall back to interactive paste.

### Implementation details

1) Create `src/lectio_sync/cookie_paste_helper.py` with:

    - `extract_cookie_header_value(raw: str) -> str`

    It should accept the common things users copy from DevTools, including:

    - A single header line: `Cookie: a=b; c=d`
    - A multi-line “Copy request headers” block that contains a `Cookie:` line
    - A “Copy as cURL” snippet that contains `-H "cookie: ..."` or `-H 'cookie: ...'`
    - The raw cookie value itself: `a=b; c=d`

    Extraction rules:

    - Find the first Cookie header occurrence (case-insensitive) and take its value.
    - If nothing looks like a header, treat the whole input as the value.
    - Reuse `_normalize_cookie_header` from src/lectio_sync/lectio_fetch.py for stripping `Cookie:` prefix and quotes.
    - Validate the result is non-empty and contains at least one `=`.

2) Add clipboard support:

    - `read_clipboard_text() -> str | None` using `tkinter`.
    - If clipboard read fails, proceed with interactive paste.

3) Add GitHub Secret update integration:

    - Shell out to `gh secret set LECTIO_COOKIE_HEADER --body <cookie>`.
    - Avoid printing the cookie value when doing this.
    - Provide `--no-gh` to disable it, and `--print-cookie` to force printing.
    - If `gh` is missing or fails, print a short error and then print the cookie (only then) so the user can paste it manually.

4) Add a clear CLI surface in src/lectio_sync/cli.py. One workable interface is:

    - `python -m lectio_sync --update-cookie-secret --from-clipboard`
    - `python -m lectio_sync --update-cookie-secret` (interactive paste)
    - Optional flags:
        - `--secret-name` (default `LECTIO_COOKIE_HEADER`)
        - `--repo` (optional; passed to `gh` as `--repo owner/name`)
        - `--print-cookie` (off by default)
        - `--no-gh` (off by default)

5) Safety:

    - Do not write the cookie to files.
    - Do not log it unless `--print-cookie` is explicitly used or `gh` update fails and the user needs manual copy.

### Acceptance

- A user can update the GitHub Secret in under 2 minutes without guessing formatting.

## Recommendation (decision point)

Implement Option C. It has the best reliability-to-effort ratio and avoids cookie scraping.

## Test plan

1) Unit tests

    - Add tests for cookie normalization and paste parsing.
    - Run:
        Working directory: C:\Users\Arthu\Lectio
        Command: py -m pytest -q
        Expected outcome: all tests pass

2) Manual validation (local)

    - Run cookie helper and confirm it produces a cookie string.
    - Run:
        py -m lectio_sync --fetch --schedule-url "<url>" --cookie-header "<cookie>" --debug-fetch
      and confirm kind=schedule-table-present (or schedule-bricks-present).

3) Manual validation (CI)

    - Update the GitHub Secret.
    - Trigger workflow_dispatch.
    - Confirm the workflow prints “Wrote <N> events to docs/calendar.ics”.

## Surprises & Discoveries

- Expected: It may not be possible to keep the cookie alive forever even with daily use (hard expiry).
- Expected: Cookie lifetime is controlled by Lectio; even a correct cookie may expire quickly and need manual re-login.

## Decision Log

- Decision (proposed): Start with Option C (paste helper) because it is dependency-free and robust.
  Rationale: MitID login must stay manual; the most valuable automation is “format it correctly and update GitHub Secret quickly”.
  Date/Author: 2026-02-26 / GitHub Copilot (GPT-5.2)

## Outcomes & Retrospective

(Leave blank until implementation is completed.)
