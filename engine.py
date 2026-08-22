"""
InkGuard Grammar Engine
=======================
Technical-documentation-aware grammar checker.
Skips: fenced code blocks, inline code, URLs, CLI flags, frontmatter,
       API paths, version strings, file paths, HTML tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ─────────────────────────────────────────────────────────────────────────────
#  Data types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class GrammarError:
    issue: str
    correction: str
    message: str
    category: str
    line: int = 0
    color: str = "#374151"


@dataclass
class CheckResult:
    original: str
    corrected: str
    highlighted: str
    errors: list[GrammarError]
    score: int
    grade: str
    word_count: int
    error_count: int
    categories: list[str]
    skipped_regions: int = 0


# ─────────────────────────────────────────────────────────────────────────────
#  Rules
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    "pronoun": "#7c3aed",
    "article": "#b45309",
    "agreement": "#dc2626",
    "punctuation": "#0369a1",
    "style": "#065f46",
    "clarity": "#9333ea",
}

GRAMMAR_RULES: list[tuple] = [
    # Pronoun — case-sensitive (lowercase i only)
    (r"\bi\b", "I", "pronoun", False, "Pronoun 'I' must always be capitalised"),
    # Article a/an
    (
        r"\ba ([aeiouAEIOU]\w*)",
        r"an \1",
        "article",
        True,
        "Use 'an' before vowel sounds",
    ),
    (
        r"\ban ([^aeiouAEIOU\s]\w*)",
        r"a \1",
        "article",
        True,
        "Use 'a' before consonant sounds",
    ),
    # Subject–verb agreement
    (
        r"\b(I|You|We|They) is\b",
        r"\1 are",
        "agreement",
        True,
        "Incorrect subject–verb agreement",
    ),
    (
        r"\b(He|She|It) are\b",
        r"\1 is",
        "agreement",
        True,
        "Singular subject requires 'is'",
    ),
    (r"\bI has\b", "I have", "agreement", True, "Incorrect tense: 'I' takes 'have'"),
    (
        r"\bHe have\b",
        "He has",
        "agreement",
        True,
        "Third-person singular requires 'has'",
    ),
    (
        r"\bShe have\b",
        "She has",
        "agreement",
        True,
        "Third-person singular requires 'has'",
    ),
    (
        r"\bIt have\b",
        "It has",
        "agreement",
        True,
        "Third-person singular requires 'has'",
    ),
    (r"\bThey has\b", "They have", "agreement", True, "Plural subject requires 'have'"),
    # Punctuation spacing
    (r"\s,", ",", "punctuation", True, "Remove space before comma"),
    (r",(?=\S)", ", ", "punctuation", True, "Add space after comma"),
    (r"\s\.", ".", "punctuation", True, "Remove space before period"),
    (r"\.\.+", ".", "punctuation", True, "Avoid repeated periods"),
    (r"\?\?+", "?", "punctuation", True, "Avoid repeated question marks"),
    (r"!!+", "!", "punctuation", True, "Avoid repeated exclamation marks"),
    # Repeated words
    (r"\b(\w+)\s+\1\b", r"\1", "style", True, "Avoid repeated consecutive words"),
    # Wordy phrases
    (r"\ba lot of\b", "many", "style", True, "Prefer concise formal expression"),
    (r"\bin order to\b", "to", "style", True, "Prefer 'to' over 'in order to'"),
    (r"\bdue to the fact that\b", "because", "style", True, "Prefer 'because'"),
    (r"\bat this point in time\b", "now", "style", True, "Prefer 'now'"),
    (r"\butilize\b", "use", "style", True, "Prefer 'use' over 'utilize'"),
    (r"\bfacilitate\b", "help", "style", True, "Prefer 'help' over 'facilitate'"),
    (r"\bleverage\b", "use", "style", True, "Prefer 'use' over 'leverage'"),
    (
        r"\bimpactful\b",
        "effective",
        "style",
        True,
        "Prefer 'effective' over 'impactful'",
    ),
    (r"\bsynergize\b", "combine", "style", True, "Prefer plain language"),
    (
        r"\bin the event that\b",
        "if",
        "clarity",
        True,
        "Prefer 'if' over 'in the event that'",
    ),
    (r"\bprior to\b", "before", "clarity", True, "Prefer 'before' over 'prior to'"),
    (
        r"\bsubsequent to\b",
        "after",
        "clarity",
        True,
        "Prefer 'after' over 'subsequent to'",
    ),
    (
        r"\bwith regard to\b",
        "about",
        "clarity",
        True,
        "Prefer 'about' over 'with regard to'",
    ),
    (
        r"\bfor the purpose of\b",
        "to",
        "clarity",
        True,
        "Prefer 'to' over 'for the purpose of'",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
#  Technical doc — regions to SKIP
# ─────────────────────────────────────────────────────────────────────────────

# Matches fenced code blocks (``` or ~~~), YAML frontmatter, HTML tags,
# inline code, URLs, CLI flags (--flag), API paths (/v1/endpoint),
# version strings (v1.2.3), file paths
SKIP_PATTERNS = [
    re.compile(r"```[\s\S]*?```", re.MULTILINE),  # fenced code
    re.compile(r"~~~[\s\S]*?~~~", re.MULTILINE),  # tilde fenced
    re.compile(r"^---[\s\S]*?^---", re.MULTILINE),  # YAML frontmatter
    re.compile(r"`[^`]+`"),  # inline code
    re.compile(r"https?://\S+"),  # URLs
    re.compile(r"<[^>]+>"),  # HTML tags
    re.compile(r"--[\w-]+=?\S*"),  # CLI flags
    re.compile(r"/[\w/.-]+"),  # file/API paths
    re.compile(r"\bv\d+\.\d+[\.\d]*\b"),  # version strings
    re.compile(r"\$\s*[\w\s./\\-]+"),  # shell commands
    re.compile(r"^\s*\|.+\|", re.MULTILINE),  # markdown tables
]


def _mask_technical_regions(text: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Replace technical regions with placeholder blanks; return masked text + regions."""
    masked = text
    regions: list[tuple[int, int, str]] = []  # (start, end, original)

    for pat in SKIP_PATTERNS:
        for m in pat.finditer(masked):
            start, end = m.start(), m.end()
            original = masked[start:end]
            placeholder = "\x00" * len(original)
            masked = masked[:start] + placeholder + masked[end:]
            regions.append((start, end, original))

    return masked, regions


def _restore_regions(text: str, regions: list[tuple[int, int, str]]) -> str:
    for start, end, original in regions:
        text = text[:start] + original + text[end:]
    return text


# ─────────────────────────────────────────────────────────────────────────────
#  Main checker
# ─────────────────────────────────────────────────────────────────────────────


def check(text: str) -> CheckResult:
    if not text or not text.strip():
        return CheckResult(
            original=text,
            corrected=text,
            highlighted=text,
            errors=[],
            score=100,
            grade="A",
            word_count=0,
            error_count=0,
            categories=[],
            skipped_regions=0,
        )

    masked, regions = _mask_technical_regions(text)
    errors: list[GrammarError] = []
    seen: set[str] = set()
    corrected = masked

    # Sentence-start capitalisation (skip inside masked regions)
    def cap_sentence(m: re.Match) -> str:
        if "\x00" in m.group():
            return m.group()
        return m.group(1) + m.group(2).upper()

    corrected = re.sub(r"(^|\.\s+)([a-z])", cap_sentence, corrected)
    if re.search(r"(^|\.\s+)([a-z])", masked):
        key = "sentence-cap"
        if key not in seen:
            seen.add(key)
            errors.append(
                GrammarError(
                    issue="lowercase sentence start",
                    correction="Capitalise the first letter",
                    message="Sentences must begin with a capital letter",
                    category="punctuation",
                    color=CATEGORY_COLORS["punctuation"],
                )
            )

    for pattern, replacement, category, use_ignorecase, explanation in GRAMMAR_RULES:
        flags = re.IGNORECASE if use_ignorecase else 0
        for m in re.finditer(pattern, corrected, flags=flags):
            if "\x00" in m.group():
                continue
            matched = m.group()
            if isinstance(replacement, str) and matched == replacement:
                continue
            key = matched.lower().strip()
            if key not in seen:
                seen.add(key)
                if isinstance(replacement, str) and "\\" not in replacement:
                    corr_str = replacement
                else:
                    corr_str = re.sub(pattern, replacement, matched, flags=flags)
                errors.append(
                    GrammarError(
                        issue=matched,
                        correction=corr_str,
                        message=explanation,
                        category=category,
                        color=CATEGORY_COLORS.get(category, "#374151"),
                    )
                )
        corrected = re.sub(pattern, replacement, corrected, flags=flags)

    # Trailing punctuation
    stripped = corrected.strip()
    if (
        stripped
        and not any("\x00" in c for c in stripped[-3:])
        and stripped[-1] not in ".!?"
    ):
        corrected = corrected.rstrip() + "."
        if "trailing-punct" not in seen:
            errors.append(
                GrammarError(
                    issue="Missing end punctuation",
                    correction=".",
                    message="Sentences should end with proper punctuation",
                    category="punctuation",
                    color=CATEGORY_COLORS["punctuation"],
                )
            )

    # Restore technical regions in corrected text
    corrected = _restore_regions(corrected, regions)

    # Score
    prose_words = len(
        [w for w in text.split() if not w.startswith(("--", "http", "/", "`"))]
    )
    score = max(0, min(100, 100 - int((len(errors) / max(prose_words, 1)) * 150)))
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"

    # Highlighted (on original text, not masked)
    highlighted = _build_highlighted(text, errors)

    return CheckResult(
        original=text,
        corrected=corrected,
        highlighted=highlighted,
        errors=errors,
        score=score,
        grade=grade,
        word_count=len(text.split()),
        error_count=len(errors),
        categories=list({e.category for e in errors}),
        skipped_regions=len(regions),
    )


def _build_highlighted(text: str, errors: list[GrammarError]) -> str:
    highlighted = text
    skip = {"Missing end punctuation", "lowercase sentence start"}
    for e in errors:
        if e.issue in skip:
            continue
        highlighted = re.sub(
            re.escape(e.issue),
            f"<mark class='ig-mark' data-cat='{e.category}' "
            f"style='--mc:{e.color}' title=\"{e.message}\">{e.issue}</mark>",
            highlighted,
            count=1,
            flags=re.IGNORECASE,
        )
    return highlighted


def result_to_dict(r: CheckResult) -> dict:
    return {
        "original": r.original,
        "corrected": r.corrected,
        "highlighted": r.highlighted,
        "errors": [
            {
                "issue": e.issue,
                "correction": e.correction,
                "message": e.message,
                "category": e.category,
                "color": e.color,
                "line": e.line,
            }
            for e in r.errors
        ],
        "score": r.score,
        "grade": r.grade,
        "word_count": r.word_count,
        "error_count": r.error_count,
        "categories": r.categories,
        "skipped_regions": r.skipped_regions,
    }
