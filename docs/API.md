# GrammarLens — API Reference

Base URL (local): `http://localhost:5000`

All request bodies are `application/json` unless noted.
All responses are `application/json` unless noted.

---

## Endpoints

### `POST /check`

Analyse a single block of text.

**Request**
```json
{ "text": "i is going to the store." }
```

**Response**
```json
{
  "corrected":   "I are going to the store.",
  "highlighted": "<mark class='gl-mark' ...>i</mark> is going ...",
  "errors": [
    {
      "issue":      "i",
      "correction": "I",
      "message":    "Pronoun 'I' must always be capitalised",
      "category":   "pronoun",
      "color":      "#7c3aed"
    }
  ],
  "score":       55,
  "grade":       "D",
  "word_count":  6,
  "error_count": 2,
  "categories":  ["pronoun", "agreement"]
}
```

**Errors**
| Status | Reason |
|--------|--------|
| 400 | `text` key missing or empty |

---

### `POST /batch`

Analyse up to 50 documents in a single call. Designed for CI pipelines.

**Request**
```json
{
  "documents": [
    { "id": "readme",       "text": "I have a dog." },
    { "id": "contributing", "text": "i is going home." }
  ]
}
```

**Response**
```json
{
  "results": [
    { "id": "readme",       "score": 100, "grade": "A", "error_count": 0, ... },
    { "id": "contributing", "score": 45,  "grade": "D", "error_count": 3, ... }
  ],
  "summary": {
    "total_documents": 2,
    "total_errors":    3,
    "average_score":   72,
    "checked_at":      "2026-05-15T10:30:00Z"
  }
}
```

Documents with empty `text` are returned with `"skipped": true`.

**Errors**
| Status | Reason |
|--------|--------|
| 400 | `documents` array missing or empty |

---

### `POST /upload`

Upload a plain-text or Markdown file.

**Request** — `multipart/form-data`
```
file=@README.md
```

**Response** — same as `/check` plus:
```json
{ "filename": "README.md" }
```

**Errors**
| Status | Reason |
|--------|--------|
| 400 | No `file` field in request |

---

### `POST /export`

Download a timestamped JSON report.

**Request**
```json
{ "text": "I have a dog." }
```

**Response** — `Content-Disposition: attachment; filename=grammarlens-report.json`
```json
{
  "corrected":    "I have a dog.",
  "errors":       [],
  "score":        100,
  "grade":        "A",
  "word_count":   5,
  "error_count":  0,
  "categories":   [],
  "generated_at": "2026-05-15T10:30:00Z"
}
```

---

## Error categories

| Category    | Examples                              |
|-------------|---------------------------------------|
| `pronoun`   | `i` → `I`                            |
| `article`   | `a apple` → `an apple`               |
| `agreement` | `They has` → `They have`             |
| `punctuation` | double periods, space before comma  |
| `style`     | `utilize` → `use`, repeated words    |

---

## Score & grade

| Grade | Score |
|-------|-------|
| A     | 90–100 |
| B     | 75–89  |
| C     | 60–74  |
| D     | 0–59   |

Score = `max(0, 100 − (errors / words) × 150)`, capped at 100.

---

## CI integration examples

### curl + jq (any CI)
```bash
RESULT=$(curl -sf -X POST http://localhost:5000/check \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$(cat README.md | tr -d '\n' | sed 's/"/\\"/g')\"}")

SCORE=$(echo "$RESULT" | jq '.score')
echo "Grammar score: $SCORE"
[ "$SCORE" -ge 80 ] || (echo "Score below threshold" && exit 1)
```

### GitHub Actions
```yaml
name: GrammarLens
on: [push, pull_request]

jobs:
  grammar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start GrammarLens
        run: |
          pip install -r requirements.txt
          python app.py &
          sleep 2

      - name: Check README
        run: |
          TEXT=$(cat README.md)
          RESULT=$(curl -sf -X POST http://localhost:5000/check \
            -H "Content-Type: application/json" \
            -d "$(jq -n --arg t "$TEXT" '{text: $t}')")
          echo "$RESULT" | jq '{score, grade, error_count}'
          SCORE=$(echo "$RESULT" | jq '.score')
          [ "$SCORE" -ge 80 ] || exit 1
```

### Batch check entire docs/ folder
```bash
DOCS=$(find docs/ -name "*.md" | head -50)
PAYLOAD=$(python3 -c "
import json, sys
docs = []
for path in '''$DOCS'''.strip().split('\n'):
    with open(path) as f:
        docs.append({'id': path, 'text': f.read()})
print(json.dumps({'documents': docs}))
")

curl -s -X POST http://localhost:5000/batch \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | jq '.summary'
```

### GitLab CI
```yaml
grammar-check:
  stage: test
  script:
    - pip install -r requirements.txt
    - python app.py &
    - sleep 2
    - |
      SCORE=$(curl -sf -X POST http://localhost:5000/check \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$(cat README.md | tr -d '\n')\"}" | jq '.score')
      echo "Score: $SCORE"
      test $SCORE -ge 80
```
