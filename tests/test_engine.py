"""Tests for InkGuard grammar engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine import check, result_to_dict


class TestTechnicalDocSkipping:
    def test_fenced_code_block_skipped(self):
        text = "Install the package.\n```bash\nhe have no errors here\n```\nDone."
        r = check(text)
        # "he have" inside code block must NOT be flagged
        issues = [e.issue.lower() for e in r.errors]
        assert "he have" not in issues

    def test_inline_code_skipped(self):
        r = check("Use `he have` as example. The server runs.")
        issues = [e.issue.lower() for e in r.errors]
        assert "he have" not in issues

    def test_cli_flags_skipped(self):
        r = check("Run with --verbose --output=file. The tool is ready.")
        # flags like --verbose should not trigger grammar rules
        assert r.score >= 90

    def test_urls_skipped(self):
        r = check("Visit https://docs.example.com/he-have for more. The page loads.")
        issues = [e.issue.lower() for e in r.errors]
        assert "he have" not in issues

    def test_skipped_regions_counted(self):
        text = "Good text.\n```python\ncode here\n```\nMore text."
        r = check(text)
        assert r.skipped_regions >= 1

    def test_prose_outside_code_still_checked(self):
        text = "```bash\necho hello\n```\ni is going home."
        r = check(text)
        assert r.error_count > 0


class TestPronounRules:
    def test_lowercase_i_caught(self):
        r = check("Yesterday i went home.")
        assert any(e.issue == "i" for e in r.errors)

    def test_capital_i_not_flagged(self):
        r = check("I went to the store.")
        assert not any(e.issue == "I" for e in r.errors)

    def test_i_mid_sentence_caught(self):
        r = check("Today i felt good.")
        assert any(e.issue == "i" for e in r.errors)


class TestArticleRules:
    def test_a_before_vowel(self):
        r = check("She ate a apple yesterday.")
        assert any("an" in e.correction for e in r.errors)

    def test_an_before_consonant(self):
        r = check("He is an developer.")
        assert any("a " in e.correction for e in r.errors)

    def test_correct_articles_pass(self):
        r = check("I have an apple and a banana.")
        cats = [e.category for e in r.errors]
        assert "article" not in cats


class TestAgreementRules:
    def test_they_has(self):
        r = check("They has many books on the shelf.")
        assert any("have" in e.correction for e in r.errors)

    def test_he_have(self):
        r = check("He have a good idea.")
        assert any("has" in e.correction for e in r.errors)

    def test_she_have(self):
        r = check("She have three cats.")
        assert any("has" in e.correction for e in r.errors)

    def test_i_has(self):
        r = check("I has a question.")
        assert any("have" in e.correction for e in r.errors)

    def test_correct_agreement_passes(self):
        r = check("She has a cat. They have many books.")
        cats = [e.category for e in r.errors]
        assert "agreement" not in cats


class TestStyleRules:
    def test_utilize_flagged(self):
        r = check("We utilize Python for this task.")
        assert any("utilize" in e.issue.lower() for e in r.errors)

    def test_a_lot_of_flagged(self):
        r = check("There are a lot of options available.")
        assert any("a lot of" in e.issue.lower() for e in r.errors)

    def test_in_order_to_flagged(self):
        r = check("In order to proceed, click next.")
        assert any("in order to" in e.issue.lower() for e in r.errors)

    def test_leverage_flagged(self):
        r = check("We leverage the framework.")
        assert any("leverage" in e.issue.lower() for e in r.errors)

    def test_prior_to_flagged(self):
        r = check("Prior to running the tests, install dependencies.")
        assert any("prior to" in e.issue.lower() for e in r.errors)


class TestScoreAndGrade:
    def test_perfect_text_scores_100(self):
        r = check("The quick brown fox jumps over the lazy dog.")
        assert r.score >= 99

    def test_clean_technical_doc_scores_high(self):
        text = "Install the package using `pip install flask`.\nRun with `python app.py --port 5000`."
        r = check(text)
        assert r.score >= 80

    def test_many_errors_scores_low(self):
        r = check("i is going he have she have they has a lot of utilize")
        assert r.score < 60

    def test_grade_a_perfect(self):
        r = check("The documentation is complete and accurate.")
        assert r.grade == "A"

    def test_grade_d_many_errors(self):
        r = check("i is going store he have apple they has book utilize leverage")
        assert r.grade in ("C", "D")

    def test_score_bounded_0_100(self):
        for text in [
            "perfect.",
            "i is he have she have they has i has utilize leverage a lot of",
        ]:
            r = check(text)
            assert 0 <= r.score <= 100


class TestResultDict:
    def test_all_keys_present(self):
        d = result_to_dict(check("I have a dog."))
        for k in (
            "original",
            "corrected",
            "highlighted",
            "errors",
            "score",
            "grade",
            "word_count",
            "error_count",
            "categories",
            "skipped_regions",
        ):
            assert k in d

    def test_errors_are_dicts(self):
        d = result_to_dict(check("i is going home."))
        for e in d["errors"]:
            assert "issue" in e and "correction" in e and "category" in e


class TestEdgeCases:
    def test_empty_string(self):
        r = check("")
        assert r.score == 100 and r.error_count == 0

    def test_whitespace_only(self):
        r = check("   \n  ")
        assert r.error_count == 0

    def test_only_code_block(self):
        r = check("```python\ni is going home\n```")
        # All content is in code block — no prose errors
        prose_errors = [
            e
            for e in r.errors
            if e.issue not in ("Missing end punctuation", "lowercase sentence start")
        ]
        assert len(prose_errors) == 0

    def test_frontmatter_skipped(self):
        text = "---\ntitle: he have errors\ndate: 2026-01-01\n---\nGood documentation."
        r = check(text)
        issues = [e.issue.lower() for e in r.errors]
        assert "he have" not in issues

    def test_long_clean_text_100(self):
        text = ("The server processes requests efficiently. " * 20).strip() + "."
        r = check(text)
        assert r.score >= 99

    def test_word_count_accurate(self):
        r = check("one two three four five.")
        assert r.word_count == 5

    def test_highlighted_contains_mark_on_error(self):
        r = check("She have a cat.")
        assert "<mark" in r.highlighted

    def test_highlighted_no_mark_on_clean(self):
        r = check("The report is complete.")
        assert "<mark" not in r.highlighted
