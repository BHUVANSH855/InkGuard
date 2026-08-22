"""
InkGuard GitHub Bot
===================
Features:
  - Label-triggered: only runs when PR has docs/documentation/content/inkguard label
  - Technical-doc aware: skips code blocks, CLI flags, API paths
  - Smart actions:
      score >= threshold → "Docs approved" comment + approve review
      score <  threshold → comment with issues + request changes
  - Updates existing comment instead of spamming
  - Configurable via env vars
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import check, result_to_dict

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH", "")
GITHUB_API = "https://api.github.com"

SCORE_THRESHOLD = int(os.environ.get("IG_SCORE_THRESHOLD", "80"))
FAIL_ON_ERROR = os.environ.get("IG_FAIL_ON_ERROR", "false").lower() == "true"
REQUIRE_LABEL = os.environ.get("IG_REQUIRE_LABEL", "true").lower() == "true"
TRIGGER_LABELS = {
    l.strip().lower()
    for l in os.environ.get(
        "IG_LABELS", "docs,documentation,content,inkguard,doc-review"
    ).split(",")
}
DOC_EXTENSIONS = {".md", ".mdx", ".txt", ".rst", ".adoc"}
BOT_MARKER = "<!-- inkguard-bot-v1 -->"

GRADE_EMOJI = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}
CAT_EMOJI = {
    "pronoun": "🔡",
    "article": "📝",
    "agreement": "⚠️",
    "punctuation": "✏️",
    "style": "💡",
    "clarity": "🔍",
}


# ── GitHub API ────────────────────────────────────────────────────────────────
def gh(method: str, path: str, body=None, accept: str = "application/vnd.github+json"):
    url = f"{GITHUB_API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": accept,
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "InkGuard-Bot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[InkGuard] API {e.code} {method} {path}: {body[:200]}", file=sys.stderr)
        return None


def get_pr_number() -> int | None:
    if not GITHUB_EVENT_PATH or not Path(GITHUB_EVENT_PATH).exists():
        return None
    with open(GITHUB_EVENT_PATH) as f:
        ev = json.load(f)
    return ev.get("pull_request", {}).get("number") or ev.get("number")


def get_pr_labels(pr_number: int) -> set[str]:
    pr = gh("GET", f"/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}")
    if not pr:
        return set()
    return {lbl["name"].lower() for lbl in pr.get("labels", [])}


def get_changed_files(pr_number: int) -> list[str]:
    files = gh("GET", f"/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}/files")
    if not files:
        return []
    return [
        f["filename"]
        for f in files
        if f.get("status") != "removed"
        and Path(f["filename"]).suffix.lower() in DOC_EXTENSIONS
    ]


def get_file_content(path: str) -> str | None:
    p = Path(path)
    if p.exists():
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    return None


def get_existing_comment(pr_number: int) -> int | None:
    comments = gh("GET", f"/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments")
    if not comments:
        return None
    for c in comments:
        if BOT_MARKER in (c.get("body") or ""):
            return c["id"]
    return None


def post_comment(pr_number: int, body: str):
    gh(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments",
        {"body": body},
    )


def update_comment(comment_id: int, body: str):
    gh(
        "PATCH",
        f"/repos/{GITHUB_REPOSITORY}/issues/comments/{comment_id}",
        {"body": body},
    )


def post_review(pr_number: int, event: str, body: str):
    """event: APPROVE | REQUEST_CHANGES | COMMENT"""
    gh(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}/reviews",
        {"event": event, "body": body},
    )


# ── Comment formatting ────────────────────────────────────────────────────────
def score_bar(score: int) -> str:
    filled = round(score / 10)
    return "█" * filled + "░" * (10 - filled) + f" {score}/100"


def format_file_section(filepath: str, r: dict) -> str:
    grade = r["grade"]
    emoji = GRADE_EMOJI.get(grade, "⚪")
    lines = [
        f"### {emoji} `{filepath}`",
        (
            f"> **Grade {grade}** &nbsp;·&nbsp; `{score_bar(r['score'])}` "
            f"&nbsp;·&nbsp; {r['error_count']} issue(s) · "
            f"{r['skipped_regions']} technical region(s) skipped"
        ),
        "",
    ]
    if not r["errors"]:
        lines += ["✅ No grammar issues found in prose sections.", ""]
        return "\n".join(lines)

    lines += [
        "<details>",
        f"<summary><b>View {len(r['errors'])} issue(s)</b></summary>",
        "",
        "| # | Category | Found | Suggestion | Rule |",
        "|---|----------|-------|------------|------|",
    ]
    for i, e in enumerate(r["errors"], 1):
        cat = e.get("category", "")
        icon = CAT_EMOJI.get(cat, "•")
        issue = str(e["issue"]).replace("|", "\\|")
        fix = str(e["correction"]).replace("|", "\\|")
        msg = str(e["message"]).replace("|", "\\|")
        lines.append(f"| {i} | {icon} {cat} | `{issue}` | `{fix}` | {msg} |")

    lines += [
        "",
        "**Suggested corrected text:**",
        "```",
        r["corrected"][:2000] + ("…" if len(r["corrected"]) > 2000 else ""),
        "```",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def build_comment(file_results: list[tuple[str, dict]], approved: bool) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_err = sum(r["error_count"] for _, r in file_results)
    avg_score = sum(r["score"] for _, r in file_results) // max(len(file_results), 1)
    header_icon = "✅" if approved else "❌"

    parts = [
        BOT_MARKER,
        f"## {header_icon} InkGuard — Documentation Review",
        "",
    ]

    if approved:
        parts += [
            "> 🎉 **Docs approved!** All documentation files meet the quality threshold.",
            "",
            (
                f"**Average score: {avg_score}/100** &nbsp;·&nbsp; "
                f"Threshold: {SCORE_THRESHOLD} &nbsp;·&nbsp; "
                f"{len(file_results)} file(s) checked"
            ),
            "",
            "---",
            "",
        ]
    else:
        parts += [
            (
                f"**Average score: {avg_score}/100** &nbsp;·&nbsp; "
                f"{total_err} total issue(s) across {len(file_results)} file(s) &nbsp;·&nbsp; "
                f"Threshold: {SCORE_THRESHOLD}"
            ),
            "",
            "> ℹ️ **Note:** Code blocks, CLI flags, URLs, and API paths are automatically skipped.",
            "",
            "---",
            "",
        ]

    for filepath, r in file_results:
        parts.append(format_file_section(filepath, r))

    parts += [
        "---",
        (
            f"<sub>🖊️ [InkGuard](https://github.com/marketplace/inkguard) bot "
            f"&nbsp;·&nbsp; {ts} &nbsp;·&nbsp; "
            f"[Configure](.github/workflows/inkguard.yml)</sub>"
        ),
    ]
    return "\n".join(parts)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    print("[InkGuard] Starting…")

    if not GITHUB_TOKEN:
        print("[InkGuard] ERROR: GITHUB_TOKEN not set.", file=sys.stderr)
        return 1

    pr_number = get_pr_number()
    if not pr_number:
        print("[InkGuard] No PR number — skipping.")
        return 0

    print(f"[InkGuard] PR #{pr_number} in {GITHUB_REPOSITORY}")

    # Label gate
    if REQUIRE_LABEL:
        labels = get_pr_labels(pr_number)
        matching = labels & TRIGGER_LABELS
        if not matching:
            print(
                f"[InkGuard] No trigger label found (need one of: {TRIGGER_LABELS}). Skipping."
            )
            return 0
        print(f"[InkGuard] Triggered by label(s): {matching}")

    changed = get_changed_files(pr_number)
    if not changed:
        print("[InkGuard] No doc files changed — nothing to check.")
        return 0

    print(f"[InkGuard] Checking {len(changed)} file(s)…")
    file_results: list[tuple[str, dict]] = []

    for filepath in changed:
        content = get_file_content(filepath)
        if not content or not content.strip():
            print(f"[InkGuard]   Skipping {filepath} (empty)")
            continue
        r = result_to_dict(check(content))
        file_results.append((filepath, r))
        print(
            f"[InkGuard]   {filepath} → score {r['score']} ({r['grade']}), "
            f"{r['error_count']} issue(s), {r['skipped_regions']} region(s) skipped"
        )

    if not file_results:
        print("[InkGuard] All files empty — nothing to report.")
        return 0

    avg_score = sum(r["score"] for _, r in file_results) // len(file_results)
    approved = avg_score >= SCORE_THRESHOLD

    comment_body = build_comment(file_results, approved)
    existing_id = get_existing_comment(pr_number)

    if existing_id:
        update_comment(existing_id, comment_body)
        print(f"[InkGuard] Updated comment #{existing_id}")
    else:
        post_comment(pr_number, comment_body)
        print("[InkGuard] Posted new comment")

    if approved:
        post_review(
            pr_number,
            "APPROVE",
            f"✅ InkGuard: Documentation approved (score {avg_score}/100)",
        )
        print("[InkGuard] Approved PR review posted")
    else:
        post_review(
            pr_number,
            "REQUEST_CHANGES",
            f"❌ InkGuard: Documentation needs attention (score {avg_score}/100, "
            f"threshold {SCORE_THRESHOLD})",
        )
        print("[InkGuard] Request-changes review posted")

    if FAIL_ON_ERROR and not approved:
        print(
            f"[InkGuard] Score {avg_score} < threshold {SCORE_THRESHOLD} — failing CI."
        )
        return 1

    print("[InkGuard] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
