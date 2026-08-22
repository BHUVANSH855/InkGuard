"""Tests for InkGuard GitHub bot — all GitHub API calls mocked."""
import json, sys, os
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bot.inkguard_bot import (
    score_bar, format_file_section, build_comment,
    BOT_MARKER, get_existing_comment, get_changed_files,
)

def make_result(score=100, grade="A", errors=None, corrected="Good.", word_count=2, skipped=0):
    errors = errors or []
    return {"score":score,"grade":grade,"errors":errors,"corrected":corrected,
            "word_count":word_count,"error_count":len(errors),"categories":[],"skipped_regions":skipped}

SAMPLE_ERR = {"issue":"i","correction":"I","message":"Pronoun 'I' must be capitalised","category":"pronoun","color":"#7c3aed"}

class TestScoreBar:
    def test_100_full(self): assert "█"*10 in score_bar(100)
    def test_0_empty(self): assert "░"*10 in score_bar(0)
    def test_50_half(self): assert "█"*5 in score_bar(50); assert "░"*5 in score_bar(50)
    def test_shows_number(self):
        for s in [0,50,100]: assert str(s) in score_bar(s)

class TestFormatFileSection:
    def test_no_errors_shows_clean(self):
        s = format_file_section("README.md", make_result())
        assert "no issues" in s

    def test_filename_present(self):
        s = format_file_section("docs/guide.md", make_result())
        assert "docs/guide.md" in s

    def test_error_shown(self):
        r = make_result(score=55, grade="D", errors=[SAMPLE_ERR])
        s = format_file_section("README.md", r)
        assert "`i`" in s
        assert "`I`" in s

    def test_pipe_escaped(self):
        err = {**SAMPLE_ERR, "issue":"a|b", "correction":"c|d"}
        s = format_file_section("f.md", make_result(errors=[err], score=50, grade="D"))
        assert "a\\|b" in s

    def test_message_shown(self):
        r = make_result(score=55, grade="D", errors=[SAMPLE_ERR])
        s = format_file_section("README.md", r)
        assert "Pronoun" in s

class TestBuildComment:
    def test_contains_marker(self):
        assert BOT_MARKER in build_comment([("README.md", make_result())], True)

    def test_approved_positive_message(self):
        c = build_comment([("README.md", make_result())], True)
        assert "no grammar issues" in c or "Looks good" in c

    def test_errors_shown_when_present(self):
        r = make_result(score=55, grade="D", errors=[SAMPLE_ERR])
        c = build_comment([("README.md", r)], False)
        assert "`i`" in c

    def test_multiple_files_present(self):
        results = [("README.md", make_result()), ("docs/g.md", make_result(score=55,grade="D",errors=[SAMPLE_ERR]))]
        c = build_comment(results, False)
        assert "docs/g.md" in c

    def test_total_errors_in_comment(self):
        results = [("a.md", make_result(errors=[SAMPLE_ERR],score=55,grade="D"))]
        c = build_comment(results, False)
        assert "1" in c

    def test_inkguard_attribution(self):
        assert "InkGuard" in build_comment([("README.md", make_result())], True)

    def test_no_score_numbers(self):
        c = build_comment([("README.md", make_result())], True)
        assert "/100" not in c

    def test_no_grade_letters(self):
        c = build_comment([("README.md", make_result())], True)
        assert "Grade A" not in c

class TestGetChangedFiles:
    def test_filters_doc_extensions(self):
        files = [
            {"filename":"README.md","status":"modified"},
            {"filename":"src/main.py","status":"modified"},
            {"filename":"docs/guide.rst","status":"modified"},
            {"filename":"old.md","status":"removed"},
        ]
        with patch("bot.inkguard_bot.gh", return_value=files):
            result = get_changed_files(1)
        assert "README.md" in result
        assert "docs/guide.rst" in result
        assert "src/main.py" not in result
        assert "old.md" not in result

    def test_returns_empty_on_api_fail(self):
        with patch("bot.inkguard_bot.gh", return_value=None):
            assert get_changed_files(1) == []

    def test_no_docs_returns_empty(self):
        with patch("bot.inkguard_bot.gh", return_value=[{"filename":"src/main.py","status":"modified"}]):
            assert get_changed_files(1) == []

class TestGetExistingComment:
    def test_finds_bot_comment(self):
        comments = [{"id":1,"body":"Regular"},{"id":2,"body":f"{BOT_MARKER}\n## Report"}]
        with patch("bot.inkguard_bot.gh", return_value=comments):
            assert get_existing_comment(1) == 2

    def test_returns_none_when_no_bot_comment(self):
        with patch("bot.inkguard_bot.gh", return_value=[{"id":1,"body":"Regular"}]):
            assert get_existing_comment(1) is None

    def test_returns_none_on_api_fail(self):
        with patch("bot.inkguard_bot.gh", return_value=None):
            assert get_existing_comment(1) is None

class TestGetPrNumber:
    def test_reads_from_event_file(self, tmp_path):
        import bot.inkguard_bot as bm
        ev = {"pull_request":{"number":42}}
        f = tmp_path/"ev.json"; f.write_text(json.dumps(ev))
        orig = bm.GITHUB_EVENT_PATH; bm.GITHUB_EVENT_PATH = str(f)
        try: assert bm.get_pr_number() == 42
        finally: bm.GITHUB_EVENT_PATH = orig

    def test_none_when_no_file(self):
        import bot.inkguard_bot as bm
        orig = bm.GITHUB_EVENT_PATH; bm.GITHUB_EVENT_PATH = "/nonexistent"
        try: assert bm.get_pr_number() is None
        finally: bm.GITHUB_EVENT_PATH = orig

class TestLabelFiltering:
    def test_matching_label_detected(self):
        from bot.inkguard_bot import TRIGGER_LABELS
        assert "docs" in TRIGGER_LABELS
        assert "documentation" in TRIGGER_LABELS
        assert "inkguard" in TRIGGER_LABELS