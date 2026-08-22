# Contributing to GrammarLens

## Setup

```bash
git clone https://github.com/your-org/grammarlens
cd grammarlens
pip install -r requirements.txt
```

## Running tests

```bash
pytest tests/ -v
```

All 55 tests must pass before submitting a PR.

## Adding a grammar rule

Rules live in `GRAMMAR_RULES` inside `app.py`. Each entry is a tuple:

```python
(pattern, replacement, category, explanation)
```

- `pattern` — Python regex
- `replacement` — string or backreference (e.g. `r"\1 are"`)
- `category` — one of `pronoun`, `article`, `agreement`, `punctuation`, `style`
- `explanation` — short human-readable reason shown in the UI

After adding a rule, add a matching test in `tests/test_grammar.py` — both a positive test (error detected) and a negative test (correct text produces no false positive).

## Project structure

```
grammarlens/
├── app.py                  # Flask app + grammar engine
├── requirements.txt
├── templates/
│   └── index.html          # Frontend
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   ├── __init__.py
│   └── test_grammar.py     # 55 pytest tests
└── docs/
    ├── API.md
    ├── DEPLOYMENT.md
    └── CONTRIBUTING.md
```

## Code style

- Python: PEP 8, type hints where practical
- JS: vanilla ES2020, no build step required
- CSS: CSS custom properties for all colours

## Pull request checklist

- [ ] All 55 existing tests pass
- [ ] New rule has a positive + negative test
- [ ] `README.md` updated if API changes
