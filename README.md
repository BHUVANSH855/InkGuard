# InkGuard 🖊️

**The documentation grammar bot for GitHub.** InkGuard automatically reviews grammar in every pull request, posts a detailed comment, and either approves or requests changes — just like a human technical writer would.

[![GitHub Marketplace](https://img.shields.io/badge/GitHub-Marketplace-blue?logo=github)](https://github.com/marketplace/inkguard)

---

## What it does

1. **Triggered by labels** — add `docs` or `documentation` to a PR
2. **Scans changed doc files** — `.md`, `.mdx`, `.txt`, `.rst`, `.adoc`
3. **Skips technical regions** — code blocks, CLI flags, URLs, API paths
4. **Posts a scored review** — grade A–D, per-file score bar, issues table
5. **Approves or requests changes** — formal GitHub review, not just a comment

## Install in 30 seconds

```yaml
# .github/workflows/inkguard.yml
name: InkGuard
on:
  pull_request:
    types: [opened, synchronize, labeled]
    paths: ["**.md", "**.txt", "**.rst"]
permissions:
  pull-requests: write
  contents: read
jobs:
  inkguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install flask
      - env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          IG_SCORE_THRESHOLD: "80"
        run: python bot/inkguard_bot.py
```

## REST API

| Endpoint | Method | Description |
|---|---|---|
| `/check` | POST | Check a single text |
| `/batch` | POST | Check up to 50 documents |
| `/upload` | POST | Upload a `.md` / `.txt` file |
| `/export` | POST | Download JSON report |
| `/health` | GET | Health check |
| `/dashboard` | GET | Web dashboard (GitHub OAuth) |

## Run locally

```bash
pip install flask
python app.py
# → http://localhost:5000
```

## Run tests

```bash
pytest tests/ -v   # 86 tests, all passing
```

## Docs

- [Setup guide](docs/SETUP.md)
- [API reference](docs/API.md)
- [Bot configuration](docs/BOT.md)

## License

MIT
