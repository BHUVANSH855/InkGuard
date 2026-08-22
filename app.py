from flask import Flask, render_template, request, jsonify, send_file
import re
import json
import io
import os
from datetime import datetime, timezone

app = Flask(__name__)

# ─────────────────────────────────────────────
#  Grammar Engine
# ─────────────────────────────────────────────

GRAMMAR_RULES = [
    # Pronoun capitalisation — case-sensitive: only match lowercase i
    (r"\bi\b", "I", "pronoun", "Pronoun 'I' must always be capitalised"),
    # Article a/an
    (r"\ba ([aeiouAEIOU]\w*)", r"an \1", "article", "Use 'an' before vowel sounds"),
    (r"\ban ([^aeiouAEIOU\s]\w*)", r"a \1", "article", "Use 'a' before consonant sounds"),
    # Subject–verb agreement
    (r"\b(I|You|We|They) is\b", r"\1 are", "agreement", "Incorrect subject–verb agreement"),
    (r"\b(He|She|It) are\b", r"\1 is", "agreement", "Singular subject requires 'is'"),
    (r"\bI has\b", "I have", "agreement", "Incorrect tense usage with 'I'"),
    (r"\bHe have\b", "He has", "agreement", "Third-person singular requires 'has'"),
    (r"\bShe have\b", "She has", "agreement", "Third-person singular requires 'has'"),
    (r"\bIt have\b", "It has", "agreement", "Third-person singular requires 'has'"),
    (r"\bThey has\b", "They have", "agreement", "Plural subject requires 'have'"),
    # Punctuation spacing
    (r"\s,", ",", "punctuation", "Remove space before comma"),
    (r",(?=\S)", ", ", "punctuation", "Add space after comma"),
    (r"\s\.", ".", "punctuation", "Remove space before period"),
    (r"\.\.+", ".", "punctuation", "Avoid repeated periods"),
    (r"\?\?+", "?", "punctuation", "Avoid repeated question marks"),
    (r"!!+", "!", "punctuation", "Avoid repeated exclamation marks"),
    (r'""+"', '"', "punctuation", "Avoid duplicate quotation marks"),
    # Repeated words
    (r"\b(\w+)\s+\1\b", r"\1", "style", "Avoid repeated consecutive words"),
    # Informal / wordy phrases
    (r"\ba lot of\b", "many", "style", "Prefer concise formal expression"),
    (r"\bin order to\b", "to", "style", "Prefer 'to' over 'in order to'"),
    (r"\bdue to the fact that\b", "because", "style", "Prefer 'because' over 'due to the fact that'"),
    (r"\bat this point in time\b", "now", "style", "Prefer 'now' over 'at this point in time'"),
    (r"\butilize\b", "use", "style", "Prefer 'use' over 'utilize'"),
    (r"\bfacilitate\b", "help", "style", "Prefer 'help' over 'facilitate' in documentation"),
    # Passive voice signal (informational only)
    (r"\bis being\b", "is being", "style", "Consider active voice instead of passive"),
]

CATEGORY_COLORS = {
    "pronoun": "#7c3aed",
    "article": "#b45309",
    "agreement": "#b91c1c",
    "punctuation": "#0369a1",
    "style": "#065f46",
}


def run_grammar_check(text: str) -> dict:
    errors = []
    seen = set()
    corrected = text

    # Sentence-start capitalisation
    def cap_sentence(m):
        return m.group(1) + m.group(2).upper()

    corrected = re.sub(r"(^|\.\s+)([a-z])", cap_sentence, corrected)
    if re.search(r"(^|\.\s+)([a-z])", text):
        if "sentence-cap" not in seen:
            seen.add("sentence-cap")
            errors.append({
                "issue": "lowercase sentence start",
                "correction": "Capitalise the first letter",
                "message": "Sentences must begin with a capital letter",
                "category": "punctuation",
                "color": CATEGORY_COLORS["punctuation"],
            })

    for pattern, replacement, category, explanation in GRAMMAR_RULES:
        # Pronoun rule is case-sensitive (we only want lowercase i, not capital I)
        flags = 0 if category == "pronoun" else re.IGNORECASE
        matches = list(re.finditer(pattern, corrected, flags=flags))
        for m in matches:
            issue = m.group()
            # Skip if the matched text already equals the replacement (no-op fix)
            expected = replacement if isinstance(replacement, str) else ""
            if isinstance(replacement, str) and issue == expected:
                continue
            issue_key = issue.lower().strip()
            if issue_key not in seen:
                seen.add(issue_key)
                correction = (
                    replacement if isinstance(replacement, str)
                    else re.sub(pattern, replacement, issue, flags=flags)
                )
                errors.append({
                    "issue": issue,
                    "correction": correction,
                    "message": explanation,
                    "category": category,
                    "color": CATEGORY_COLORS.get(category, "#374151"),
                })
        corrected = re.sub(pattern, replacement, corrected, flags=flags)

    # Trailing punctuation
    if corrected.strip() and corrected.strip()[-1] not in ".!?":
        corrected = corrected.rstrip() + "."
        if "trailing-punct" not in seen:
            errors.append({
                "issue": "Missing end punctuation",
                "correction": ".",
                "message": "Sentences should end with proper punctuation",
                "category": "punctuation",
                "color": CATEGORY_COLORS["punctuation"],
            })

    total = len(text.split())
    error_count = len(errors)
    score = max(0, min(100, 100 - int((error_count / max(total, 1)) * 150)))
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"

    return {
        "corrected": corrected,
        "errors": errors,
        "score": score,
        "grade": grade,
        "word_count": total,
        "error_count": error_count,
        "categories": list({e["category"] for e in errors}),
    }


def highlight_errors(text: str, errors: list) -> str:
    highlighted = text
    for e in errors:
        if e["issue"] not in ("Missing end punctuation", "lowercase sentence start"):
            color = e.get("color", "#b91c1c")
            highlighted = re.sub(
                re.escape(e["issue"]),
                f"<mark class='gl-mark' data-cat='{e['category']}' style='--mark-color:{color}' title=\"{e['message']}\">{e['issue']}</mark>",
                highlighted,
                count=1,
                flags=re.IGNORECASE,
            )
    return highlighted


# ─────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = run_grammar_check(text)
    result["highlighted"] = highlight_errors(text, result["errors"])
    return jsonify(result)


@app.route("/batch", methods=["POST"])
def batch():
    """
    Accept JSON: { "documents": [{"id": "readme", "text": "..."}, ...] }
    Returns per-document results + aggregate summary.
    Designed for CI pipelines and documentation bots.
    """
    data = request.get_json(silent=True) or {}
    docs = data.get("documents", [])
    if not docs:
        return jsonify({"error": "No documents provided"}), 400

    results = []
    for doc in docs[:50]:  # cap at 50
        doc_id = doc.get("id", "unnamed")
        text = doc.get("text", "")
        if not text.strip():
            results.append({"id": doc_id, "skipped": True})
            continue
        r = run_grammar_check(text)
        r["highlighted"] = highlight_errors(text, r["errors"])
        r["id"] = doc_id
        results.append(r)

    total_errors = sum(r.get("error_count", 0) for r in results if not r.get("skipped"))
    avg_score = (
        sum(r.get("score", 0) for r in results if not r.get("skipped"))
        // max(1, sum(1 for r in results if not r.get("skipped")))
    )

    return jsonify({
        "results": results,
        "summary": {
            "total_documents": len(docs),
            "total_errors": total_errors,
            "average_score": avg_score,
            "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    })


@app.route("/upload", methods=["POST"])
def upload():
    """Accept a plain-text file upload and return grammar results."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        text = f.read().decode("utf-8", errors="replace")
    except Exception:
        return jsonify({"error": "Could not read file"}), 400

    result = run_grammar_check(text)
    result["highlighted"] = highlight_errors(text, result["errors"])
    result["filename"] = f.filename
    return jsonify(result)


@app.route("/export", methods=["POST"])
def export_report():
    """Return a JSON report ready for download."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    result = run_grammar_check(text)
    result["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result.pop("highlighted", None)

    buf = io.BytesIO(json.dumps(result, indent=2).encode())
    buf.seek(0)
    return send_file(buf, mimetype="application/json",
                     as_attachment=True, download_name="grammarlens-report.json")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
