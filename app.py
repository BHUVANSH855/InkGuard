"""
InkGuard — Flask API
Endpoints: /check  /batch  /upload  /export  /health
Dashboard: /dashboard  /auth/github  /auth/callback  /auth/logout
"""

from __future__ import annotations

import io
import json
import os
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from engine import check, result_to_dict

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# GitHub OAuth
GH_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GH_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GH_OAUTH_URL = "https://github.com/login/oauth/authorize"
GH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GH_USER_URL = "https://api.github.com/user"

# In-memory scan history (replace with DB in production)
_scan_history: list[dict] = []

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _gh_api(url: str, token: str) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "InkGuard-Bot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.URLError:
        return None


def _login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("dashboard_login"))
        return f(*args, **kwargs)

    return wrapped


# ─────────────────────────────────────────────
#  Public landing page
# ─────────────────────────────────────────────


@app.route("/")
def index():
    return render_template("landing.html")


# ─────────────────────────────────────────────
#  Grammar API
# ─────────────────────────────────────────────


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0", "name": "InkGuard"})


@app.route("/check", methods=["POST"])
def api_check():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    result = check(text)
    d = result_to_dict(result)
    _scan_history.append(
        {
            "source": data.get("source", "api"),
            "score": d["score"],
            "grade": d["grade"],
            "error_count": d["error_count"],
            "word_count": d["word_count"],
            "checked_at": _now(),
        }
    )
    return jsonify(d)


@app.route("/batch", methods=["POST"])
def api_batch():
    data = request.get_json(silent=True) or {}
    docs = data.get("documents", [])
    if not docs:
        return jsonify({"error": "No documents provided"}), 400
    results = []
    for doc in docs[:50]:
        doc_id = doc.get("id", "unnamed")
        text = doc.get("text", "")
        if not text.strip():
            results.append({"id": doc_id, "skipped": True})
            continue
        r = result_to_dict(check(text))
        r["id"] = doc_id
        results.append(r)
    checked = [r for r in results if not r.get("skipped")]
    avg = sum(r["score"] for r in checked) // max(len(checked), 1)
    total_err = sum(r["error_count"] for r in checked)
    return jsonify(
        {
            "results": results,
            "summary": {
                "total_documents": len(docs),
                "checked": len(checked),
                "total_errors": total_err,
                "average_score": avg,
                "checked_at": _now(),
            },
        }
    )


@app.route("/upload", methods=["POST"])
def api_upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    text = f.read().decode("utf-8", errors="replace")
    r = result_to_dict(check(text))
    r["filename"] = f.filename
    return jsonify(r)


@app.route("/export", methods=["POST"])
def api_export():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    r = result_to_dict(check(text))
    r["generated_at"] = _now()
    r.pop("highlighted", None)
    buf = io.BytesIO(json.dumps(r, indent=2).encode())
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name="inkguard-report.json",
    )


# ─────────────────────────────────────────────
#  Dashboard — GitHub OAuth
# ─────────────────────────────────────────────


@app.route("/dashboard/login")
def dashboard_login():
    return render_template(
        "dashboard_login.html", gh_client_id=GH_CLIENT_ID, has_oauth=bool(GH_CLIENT_ID)
    )


@app.route("/auth/github")
def auth_github():
    state = secrets.token_hex(16)
    session["oauth_state"] = state
    params = urllib.parse.urlencode(
        {
            "client_id": GH_CLIENT_ID,
            "redirect_uri": url_for("auth_callback", _external=True),
            "scope": "read:user",
            "state": state,
        }
    )
    return redirect(f"{GH_OAUTH_URL}?{params}")


@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or state != session.pop("oauth_state", None):
        return redirect(url_for("dashboard_login"))
    # Exchange code for token
    token_data = urllib.parse.urlencode(
        {
            "client_id": GH_CLIENT_ID,
            "client_secret": GH_CLIENT_SECRET,
            "code": code,
        }
    ).encode()
    req = urllib.request.Request(
        GH_TOKEN_URL,
        data=token_data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            token_resp = json.loads(resp.read())
    except urllib.error.URLError:
        return redirect(url_for("dashboard_login"))
    access_token = token_resp.get("access_token")
    if not access_token:
        return redirect(url_for("dashboard_login"))
    user = _gh_api(GH_USER_URL, access_token)
    if not user:
        return redirect(url_for("dashboard_login"))
    session["user"] = {
        "login": user.get("login"),
        "name": user.get("name") or user.get("login"),
        "avatar": user.get("avatar_url"),
        "token": access_token,
    }
    return redirect(url_for("dashboard"))


@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@_login_required
def dashboard():
    user = session["user"]
    recent = list(reversed(_scan_history[-50:]))
    total = len(_scan_history)
    avg = (sum(s["score"] for s in _scan_history) // total) if total else 0
    total_errors = sum(s["error_count"] for s in _scan_history)
    return render_template(
        "dashboard.html",
        user=user,
        recent=recent,
        total=total,
        avg_score=avg,
        total_errors=total_errors,
    )


@app.route("/dashboard/scan")
@_login_required
def dashboard_scan():
    return render_template("dashboard_scan.html", user=session["user"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)
