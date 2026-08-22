# InkGuard — Setup Guide

## 5-minute install

### Step 1: Add the workflow
Copy `.github/workflows/inkguard.yml` into your repository.

### Step 2: Label your PRs
Add a `docs`, `documentation`, or `inkguard` label to any PR that touches documentation files. InkGuard only activates when a trigger label is present — no noise on code-only PRs.

### Step 3: Watch InkGuard review
InkGuard posts a comment with per-file scores and either:
- ✅ Approves the PR ("Docs approved!")
- ❌ Requests changes with an issues table

## Configuration

All settings are environment variables in the workflow file:

| Variable | Default | Description |
|---|---|---|
| `IG_SCORE_THRESHOLD` | `80` | Minimum passing score |
| `IG_FAIL_ON_ERROR` | `false` | Exit 1 to block merges |
| `IG_REQUIRE_LABEL` | `true` | Only run on labelled PRs |
| `IG_LABELS` | `docs,documentation,content,inkguard,doc-review` | Trigger labels |

## Dashboard (optional)

Set these environment variables to enable GitHub OAuth:
```
GITHUB_CLIENT_ID=your_app_client_id
GITHUB_CLIENT_SECRET=your_app_client_secret
SECRET_KEY=random_hex_string
```

Create a GitHub OAuth App at: Settings → Developer settings → OAuth Apps
Set callback URL to: `https://your-domain.com/auth/callback`

## What gets skipped

InkGuard is technical-doc aware. These regions are never checked:
- Fenced code blocks (`` ``` `` and `~~~`)
- Inline code (`` `like this` ``)
- YAML frontmatter (`---..---`)
- URLs (`https://...`)
- CLI flags (`--flag`, `--option=value`)
- File/API paths (`/v1/endpoint`, `./path/to/file`)
- Version strings (`v1.2.3`)
- HTML tags
- Markdown tables

## GitHub Marketplace listing

Required files for Marketplace submission:
- `action/action.yml` ✅ included
- `README.md` ✅ included
- `LICENSE` — add MIT license file
- Marketplace icon: branding set to `edit-3` / blue ✅

Submit at: https://github.com/marketplace/new
