# GrammarLens

**Documentation-grade grammar checking for teams, repos, and CI pipelines.**

GrammarLens is a self-hosted grammar analysis tool built to be used as a drop-in linter for documentation. It ships as a Python/Flask web app with a clean REST API that any pipeline, bot, or editor integration can call.

---

## Quickstart

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

## Run tests

```bash
pytest tests/ -v
# 55 passed
```

---

## Features

| Feature | Details |
|---|---|
| Grammar engine | 20+ rules: pronoun case, a/an, subject–verb agreement, punctuation, style |
| Accuracy score | 0–100 score + letter grade per document |
| Annotated output | HTML with inline highlights, colour-coded by error category |
| Batch API | `/batch` — up to 50 documents, aggregate summary |
| File upload | `/upload` — POST a `.txt` / `.md` file directly |
| JSON export | `/export` — downloadable machine-readable report |
| CI-ready | Works with `curl` + `jq` in GitHub Actions / GitLab CI |

---

## REST API

### Single document
```bash
curl -X POST http://localhost:5000/check \
  -H "Content-Type: application/json" \
  -d '{"text": "i is going to the store"}'
```

### Batch (CI pipelines)
```bash
curl -X POST http://localhost:5000/batch \
  -H "Content-Type: application/json" \
  -d '{"documents":[{"id":"readme","text":"..."},{"id":"contrib","text":"..."}]}'
```

### File upload
```bash
curl -X POST http://localhost:5000/upload -F "file=@README.md"
```

### Export report
```bash
curl -X POST http://localhost:5000/export \
  -H "Content-Type: application/json" \
  -d '{"text":"..."}' -o report.json
```

Full API reference: [docs/API.md](docs/API.md)

---

## GitHub Actions

```yaml
- name: GrammarLens check
  run: |
    python app.py &
    sleep 2
    SCORE=$(curl -sf -X POST http://localhost:5000/check \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg t "$(cat README.md)" '{text:$t}')" \
      | jq '.score')
    echo "Grammar score: $SCORE"
    [ "$SCORE" -ge 80 ] || exit 1
```

---

## Error categories

| Category | Examples |
|---|---|
| `pronoun` | `i` → `I` |
| `article` | `a apple` → `an apple` |
| `agreement` | `They has` → `They have` |
| `punctuation` | double periods, space before comma |
| `style` | `utilize` → `use`, repeated words |

---

## Docs

- [API Reference](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Contributing](docs/CONTRIBUTING.md)

## License

MIT
