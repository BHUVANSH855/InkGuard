"""
GrammarLens — Test Suite
Run:  pytest tests/ -v
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, run_grammar_check, highlight_errors


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ─────────────────────────────────────────────
#  Grammar engine — unit tests
# ─────────────────────────────────────────────

class TestPronounCapitalisation:
    def test_lowercase_i_corrected(self):
        r = run_grammar_check("i went to the store.")
        assert "I" in r["corrected"]

    def test_uppercase_i_unchanged(self):
        r = run_grammar_check("I went to the store.")
        assert r["error_count"] == 0

    def test_i_mid_sentence(self):
        r = run_grammar_check("Yesterday i saw a dog.")
        assert "i" not in r["corrected"]


class TestArticles:
    def test_a_before_vowel(self):
        r = run_grammar_check("She ate a apple.")
        assert "an apple" in r["corrected"]

    def test_an_before_consonant(self):
        r = run_grammar_check("He is an developer.")
        assert "a developer" in r["corrected"]

    def test_correct_article_no_error(self):
        r = run_grammar_check("She ate an apple.")
        # no article errors
        cats = [e["category"] for e in r["errors"]]
        assert "article" not in cats


class TestSubjectVerbAgreement:
    def test_i_is(self):
        r = run_grammar_check("I is going home.")
        assert "I are" in r["corrected"]

    def test_he_have(self):
        r = run_grammar_check("He have a car.")
        assert "He has" in r["corrected"]

    def test_she_have(self):
        r = run_grammar_check("She have a cat.")
        assert "She has" in r["corrected"]

    def test_they_has(self):
        r = run_grammar_check("They has many books.")
        assert "They have" in r["corrected"]

    def test_i_has(self):
        r = run_grammar_check("I has a dog.")
        assert "I have" in r["corrected"]

    def test_correct_agreement_no_error(self):
        r = run_grammar_check("She has a cat.")
        cats = [e["category"] for e in r["errors"]]
        assert "agreement" not in cats


class TestPunctuation:
    def test_space_before_comma(self):
        r = run_grammar_check("Hello , world.")
        assert " ," not in r["corrected"]

    def test_no_space_after_comma(self):
        r = run_grammar_check("apples,oranges,bananas.")
        # sentence start gets capitalised, so check case-insensitively
        assert ", " in r["corrected"]

    def test_double_period(self):
        r = run_grammar_check("End of sentence..")
        assert ".." not in r["corrected"]

    def test_double_question_mark(self):
        r = run_grammar_check("Really??")
        assert "??" not in r["corrected"]

    def test_missing_end_punctuation(self):
        r = run_grammar_check("This sentence has no end")
        assert r["corrected"].endswith(".")

    def test_existing_punctuation_ok(self):
        r = run_grammar_check("Does this work?")
        cats = [e["category"] for e in r["errors"]]
        assert "punctuation" not in cats


class TestStyle:
    def test_repeated_word(self):
        r = run_grammar_check("the the dog ran fast.")
        corrected = r["corrected"].lower()
        assert "the the" not in corrected

    def test_a_lot_of(self):
        r = run_grammar_check("There are a lot of bugs.")
        assert "many" in r["corrected"]

    def test_utilize(self):
        r = run_grammar_check("We utilize Python.")
        assert "use" in r["corrected"].lower()

    def test_in_order_to(self):
        r = run_grammar_check("In order to run the tests, install pytest.")
        assert "in order to" not in r["corrected"].lower()


class TestScore:
    def test_perfect_text_score_100(self):
        r = run_grammar_check("The quick brown fox jumps over the lazy dog.")
        assert r["score"] == 100

    def test_error_text_lower_score(self):
        r = run_grammar_check("i is going store he have a apple")
        assert r["score"] < 80

    def test_score_between_0_and_100(self):
        for text in [
            "perfect sentence here.",
            "i is bad grammar he have apple",
            "We utilize a lot of resources in order to facilitate growth.",
        ]:
            r = run_grammar_check(text)
            assert 0 <= r["score"] <= 100

    def test_grade_a_for_perfect(self):
        r = run_grammar_check("The report is complete and accurate.")
        assert r["grade"] == "A"

    def test_grade_d_for_many_errors(self):
        r = run_grammar_check("i is going he have she have they has i has utilize a lot of")
        assert r["grade"] in ("C", "D")


class TestWordCount:
    def test_word_count_accurate(self):
        r = run_grammar_check("one two three four five.")
        assert r["word_count"] == 5

    def test_empty_text(self):
        r = run_grammar_check("  ")
        assert r["word_count"] == 0


class TestHighlightErrors:
    def test_highlight_wraps_error(self):
        text = "She have a cat."
        r = run_grammar_check(text)
        html = highlight_errors(text, r["errors"])
        assert "<mark" in html

    def test_highlight_no_errors(self):
        text = "The server started successfully."
        r = run_grammar_check(text)
        html = highlight_errors(text, r["errors"])
        assert "<mark" not in html


class TestCategories:
    def test_error_has_category(self):
        r = run_grammar_check("i is going home.")
        for e in r["errors"]:
            assert "category" in e
            assert e["category"] in ("pronoun", "article", "agreement", "punctuation", "style")

    def test_categories_list_populated(self):
        r = run_grammar_check("i is going home.")
        assert len(r["categories"]) > 0


# ─────────────────────────────────────────────
#  API — /check endpoint
# ─────────────────────────────────────────────

class TestCheckEndpoint:
    def test_post_returns_200(self, client):
        res = client.post("/check",
                          data=json.dumps({"text": "I have a dog."}),
                          content_type="application/json")
        assert res.status_code == 200

    def test_response_has_required_keys(self, client):
        res = client.post("/check",
                          data=json.dumps({"text": "i is going."}),
                          content_type="application/json")
        data = res.get_json()
        for key in ("corrected", "errors", "score", "grade", "word_count", "error_count", "highlighted"):
            assert key in data, f"Missing key: {key}"

    def test_empty_text_returns_400(self, client):
        res = client.post("/check",
                          data=json.dumps({"text": ""}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_missing_text_key_returns_400(self, client):
        res = client.post("/check",
                          data=json.dumps({}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_correct_grammar_score_100(self, client):
        res = client.post("/check",
                          data=json.dumps({"text": "The server is running correctly."}),
                          content_type="application/json")
        assert res.get_json()["score"] == 100

    def test_errors_corrected(self, client):
        res = client.post("/check",
                          data=json.dumps({"text": "i is going home."}),
                          content_type="application/json")
        data = res.get_json()
        assert data["error_count"] > 0
        assert "I" in data["corrected"]


# ─────────────────────────────────────────────
#  API — /batch endpoint
# ─────────────────────────────────────────────

class TestBatchEndpoint:
    def test_batch_returns_200(self, client):
        payload = {"documents": [{"id": "d1", "text": "I have a dog."}]}
        res = client.post("/batch",
                          data=json.dumps(payload),
                          content_type="application/json")
        assert res.status_code == 200

    def test_batch_summary_present(self, client):
        payload = {"documents": [
            {"id": "a", "text": "I have a dog."},
            {"id": "b", "text": "i is going home."},
        ]}
        res = client.post("/batch",
                          data=json.dumps(payload),
                          content_type="application/json")
        data = res.get_json()
        assert "summary" in data
        assert "total_errors" in data["summary"]
        assert "average_score" in data["summary"]

    def test_batch_results_count_matches(self, client):
        docs = [{"id": str(i), "text": "I have a dog."} for i in range(5)]
        res = client.post("/batch",
                          data=json.dumps({"documents": docs}),
                          content_type="application/json")
        data = res.get_json()
        assert len(data["results"]) == 5

    def test_empty_documents_returns_400(self, client):
        res = client.post("/batch",
                          data=json.dumps({"documents": []}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_batch_caps_at_50(self, client):
        docs = [{"id": str(i), "text": "I have a dog."} for i in range(60)]
        res = client.post("/batch",
                          data=json.dumps({"documents": docs}),
                          content_type="application/json")
        data = res.get_json()
        assert len(data["results"]) <= 50

    def test_batch_skips_empty_text(self, client):
        payload = {"documents": [
            {"id": "a", "text": "I have a dog."},
            {"id": "b", "text": ""},
        ]}
        res = client.post("/batch",
                          data=json.dumps(payload),
                          content_type="application/json")
        data = res.get_json()
        skipped = [r for r in data["results"] if r.get("skipped")]
        assert len(skipped) == 1


# ─────────────────────────────────────────────
#  API — /upload endpoint
# ─────────────────────────────────────────────

class TestUploadEndpoint:
    def test_upload_txt_file(self, client):
        data = {"file": (b"i is going to the store.", "test.txt")}
        res = client.post("/upload",
                          data={"file": (b"i is going to the store.", "test.txt")},
                          content_type="multipart/form-data")
        # Flask test client needs BytesIO
        from io import BytesIO
        file_data = BytesIO(b"i is going to the store.")
        res = client.post("/upload",
                          data={"file": (file_data, "test.txt")},
                          content_type="multipart/form-data")
        assert res.status_code == 200
        body = res.get_json()
        assert "corrected" in body
        assert body["filename"] == "test.txt"

    def test_upload_no_file_returns_400(self, client):
        res = client.post("/upload", data={}, content_type="multipart/form-data")
        assert res.status_code == 400


# ─────────────────────────────────────────────
#  API — /export endpoint
# ─────────────────────────────────────────────

class TestExportEndpoint:
    def test_export_returns_json_file(self, client):
        res = client.post("/export",
                          data=json.dumps({"text": "I have a dog."}),
                          content_type="application/json")
        assert res.status_code == 200
        assert "application/json" in res.content_type
        body = res.get_json()
        assert "corrected" in body
        assert "generated_at" in body

    def test_export_has_timestamp(self, client):
        res = client.post("/export",
                          data=json.dumps({"text": "I have a dog."}),
                          content_type="application/json")
        body = res.get_json()
        assert body["generated_at"].endswith("Z")


# ─────────────────────────────────────────────
#  Index route
# ─────────────────────────────────────────────

class TestIndexRoute:
    def test_index_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"GrammarLens" in res.data


# ─────────────────────────────────────────────
#  Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:
    def test_single_word(self):
        r = run_grammar_check("Hello")
        assert isinstance(r["score"], int)

    def test_long_text(self):
        text = ("I have a dog. " * 50).strip()
        r = run_grammar_check(text)
        assert r["score"] == 100

    def test_only_punctuation(self):
        r = run_grammar_check("...")
        assert isinstance(r["corrected"], str)

    def test_numbers_in_text(self):
        r = run_grammar_check("I have three dogs and two cats.")
        assert r["score"] == 100

    def test_mixed_case_no_false_positive(self):
        r = run_grammar_check("The API returns JSON data.")
        cats = [e["category"] for e in r["errors"]]
        assert "agreement" not in cats
