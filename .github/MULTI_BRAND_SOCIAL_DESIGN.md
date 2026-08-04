# Multi-Brand Social Media Posting System

## Architecture Overview

This system enables automatic posting to social media (Twitter, LinkedIn, Bluesky, Instagram, Facebook) from blog posts, with support for multiple brands (dlockamy, Lockamy Studios, Spec-Up) and selective cross-posting based on configuration.

## Directory Structure

```
dlockamy.com/blog/
├── brands/
│   ├── dlockamy/
│   │   ├── brand.yml              # Brand metadata
│   │   ├── posts/                 # Blog posts for this brand
│   │   │   ├── 2026-07-15-post-1.md
│   │   │   └── 2026-08-01-post-2.md
│   │   └── _posts/                # Alternative Jekyll structure (optional)
│   │
│   ├── lockamystudios/
│   │   ├── brand.yml
│   │   └── posts/
│   │
│   └── spec-up/
│       ├── brand.yml
│       └── posts/
│
├── .github/
│   ├── social-config.yml          # Central routing & platform config
│   └── workflows/
│       └── auto-post-social.yml    # GitHub Actions automation
│
└── ... (rest of blog structure)
```

## Configuration Files

### `.github/social-config.yml` — Central Routing

Defines all brands, their social media handles, platform credentials, and cross-posting rules:

```yaml
brands:
  dlockamy:
    platforms:
      twitter:
        enabled: true
        handle: dlockamy
        secret_key: SOCIAL_CREDS_DLOCKAMY
      linkedin:
        enabled: true
        handle: dlockamy
        secret_key: SOCIAL_CREDS_DLOCKAMY
      bluesky:
        enabled: true
        handle: dlockamy.com
        secret_key: SOCIAL_CREDS_DLOCKAMY
      instagram:
        enabled: false
      facebook:
        enabled: false
    hashtags:
      - "#softwareeng"
      - "#rust"
      - "#openprotocol"
    mention_brands: []

  lockamystudios:
    platforms:
      twitter:
        enabled: true
        handle: LockamyStudios
        secret_key: SOCIAL_CREDS_LOCKAMYSTUDIOS
      linkedin:
        enabled: true
        handle: lockamy-studios
        secret_key: SOCIAL_CREDS_LOCKAMYSTUDIOS
      bluesky:
        enabled: true
        handle: lockamystudios.com
        secret_key: SOCIAL_CREDS_LOCKAMYSTUDIOS
      instagram:
        enabled: false
      facebook:
        enabled: true
        secret_key: SOCIAL_CREDS_LOCKAMYSTUDIOS
    hashtags:
      - "#design"
      - "#hardware"
      - "#protocol"
    mention_brands: []

  spec-up:
    platforms:
      twitter:
        enabled: true
        handle: spec_up_io
        secret_key: SOCIAL_CREDS_SPEC_UP
      linkedin:
        enabled: true
        handle: spec-up-io
        secret_key: SOCIAL_CREDS_SPEC_UP
      bluesky:
        enabled: false
      instagram:
        enabled: false
      facebook:
        enabled: false
    hashtags:
      - "#quoting"
      - "#manufacturing"
    mention_brands: ["dlockamy"]  # Mention @dlockamy on posts
```

### `brands/*/brand.yml` — Brand Metadata

Per-brand configuration with voice, tone, and URL:

```yaml
# brands/dlockamy/brand.yml
name: dlockamy
title: "Douglas Lockamy's Engineering Log"
url: https://dlockamy.com
tagline: "Building protocols and systems"
voice:
  tone: technical, thoughtful, direct
  audience: engineers, protocol designers, open-source community
  content_type: deep technical posts, system design, protocol work

# brands/lockamystudios/brand.yml
name: Lockamy Studios
title: "Lockamy Studios"
url: https://lockamystudios.com
tagline: "Design + Hardware + Protocol"
voice:
  tone: refined, craft-focused, ambitious
  audience: design community, makers, consumers
  content_type: design philosophy, hardware releases, brand announcements

# brands/spec-up/brand.yml
name: Spec-Up
title: "Spec-Up: Quote-to-Ship"
url: https://app.spec-up.com
tagline: "Manufacturing quote automation"
voice:
  tone: professional, clear, product-focused
  audience: manufacturers, procurement engineers, product teams
  content_type: feature releases, use cases, manufacturing insights
```

## Blog Post Format

Posts live in `brands/*/posts/*.md` as Markdown with YAML frontmatter:

```markdown
---
title: "How We Built the Quickring Hub Protocol"
date: 2026-08-01
brands:
  - dlockamy
  - lockamystudios
excerpt: "A deep dive into the message envelope design and wire protocol we use in Quickring's device fabric."

# Optional: platform-specific overrides
social_overrides:
  twitter: "🧵 New blog post: How we designed the Quickring Hub protocol for fanout at scale. Read more: {url}"
  linkedin: "Our approach to building a protocol that scales to thousands of subscriptions per device."
---

## The Challenge

We needed a protocol that could handle...

... rest of post content ...
```

### Frontmatter Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | ✓ | Post title |
| `date` | YYYY-MM-DD | ✓ | Publication date |
| `brands` | array | Optional* | Which brands receive this post (default: brand from path) |
| `excerpt` | string | Optional | Social preview text (default: first 200 chars of body) |
| `social_overrides` | object | Optional | Platform-specific post text (twitter, linkedin, bluesky, facebook) |

*If `brands` not specified, workflow infers brand from path: `brands/dlockamy/posts/...` → dlockamy brand.

## Workflow Behavior

### Auto-trigger (on push)

1. **Detect changed posts**: Finds all `.md` files in `brands/*/posts/` that changed
2. **Parse frontmatter**: Extracts title, date, brands, excerpt, social_overrides
3. **Generate posts**: Creates platform-specific text per brand per platform
4. **Post to APIs**: Sends to enabled platforms (Twitter/Tweepy, LinkedIn/requests, Bluesky/atproto)
5. **Notify**: Sends Slack message on success/failure

### Manual trigger (`workflow_dispatch`)

Run via GitHub Actions UI with optional `brand` input:
- `brand: all` (default) — posts to all brands
- `brand: dlockamy` — posts only the dlockamy brand

Useful for re-posting old content or manual control.

## Secret Management

Store per-brand credentials in GitHub Secrets as JSON:

### `SOCIAL_CREDS_DLOCKAMY`
```json
{
  "twitter": {
    "api_key": "...",
    "api_secret": "...",
    "access_token": "...",
    "access_secret": "..."
  },
  "linkedin": {
    "token": "...oauth2_token..."
  },
  "bluesky": {
    "handle": "@dlockamy.com",
    "password": "...app-specific-password..."
  }
}
```

### `SOCIAL_CREDS_LOCKAMYSTUDIOS`
```json
{
  "twitter": { ... },
  "linkedin": { ... },
  "bluesky": { ... },
  "facebook": {
    "page_access_token": "...",
    "page_id": "..."
  }
}
```

### `SOCIAL_CREDS_SPEC_UP`
```json
{
  "twitter": { ... },
  "linkedin": { ... }
}
```

### `SLACK_WEBHOOK_URL`
```
https://hooks.slack.com/services/T.../B.../...
```

## Platform-Specific Features

### Twitter/X (via Tweepy)

- **Default text**: `{emoji if resurfaced} {title}\n\n{date if resurfaced}{url}\n\n{hashtags} {mentions}`
- **Override key**: `social_overrides.twitter`
- **Character limit**: 280 (Tweepy enforces)
- **Hashtags**: Added automatically from config
- **Cross-mentions**: `@brand_name` appended if configured in `mention_brands`

### LinkedIn (via requests + REST API)

- **Default text**: `{emoji if resurfaced} {title}\n\n{date if resurfaced}{excerpt}\n\nRead more: {url}`
- **Override key**: `social_overrides.linkedin`
- **Visibility**: Always PUBLIC
- **Requires**: OAuth2 token (user access token, not page token)

### Bluesky (via atproto SDK)

- **Default text**: `{emoji if resurfaced} {title}\n\n{date if resurfaced}{url}`
- **Override key**: `social_overrides.bluesky`
- **Auth**: App-specific password (not master password)
- **Character limit**: 300 characters

### Instagram (placeholder)

- Not implemented yet
- Requires Instagram Graph API + business account
- Image extraction from post needed
- Add config structure when ready

### Facebook (placeholder)

- Not implemented yet
- Requires Facebook Graph API + page token
- Image and link preview handling needed
- Add config structure when ready

## Resurfacing Old Content

Posts older than **90 days** are flagged as "resurfaced" and get a `🔄` prefix to distinguish them from new content:

```python
is_resurfaced = (datetime.now() - post_date).days > 90
```

This allows selective re-promotion of evergreen content without cluttering feeds with "fake news."

## Implementation Checklist

### Phase 1: Configuration Setup (Immediate)

- [ ] Create `.github/social-config.yml` with all brands and platforms
- [ ] Create `brands/dlockamy/brand.yml`, `brands/lockamystudios/brand.yml`, `brands/spec-up/brand.yml`
- [ ] Add `SOCIAL_CREDS_DLOCKAMY`, `SOCIAL_CREDS_LOCKAMYSTUDIOS`, `SOCIAL_CREDS_SPEC_UP` secrets to GitHub
- [ ] Add `SLACK_WEBHOOK_URL` secret
- [ ] Verify workflow file exists: `.github/workflows/auto-post-social.yml`

### Phase 2: Credential Setup (Per-Platform)

**Twitter/X:**
- [ ] Create/verify app at developer.twitter.com
- [ ] Generate API keys + access tokens
- [ ] Store in `SOCIAL_CREDS_*` JSON (per brand)

**LinkedIn:**
- [ ] Register app at linkedin.com/developers
- [ ] Generate OAuth2 token (user access, not page)
- [ ] Store in `SOCIAL_CREDS_*` JSON

**Bluesky:**
- [ ] Create app password at bsky.app/settings/app-passwords
- [ ] Store in `SOCIAL_CREDS_*` JSON (handle + password)

**Slack:**
- [ ] Create webhook at api.slack.com/apps
- [ ] Store `SLACK_WEBHOOK_URL` secret

### Phase 3: Content Structure (Ongoing)

- [ ] Organize existing blog posts into `brands/*/posts/`
- [ ] Add YAML frontmatter to all posts (title, date, brands, excerpt)
- [ ] Test workflow on a new post in a feature branch

### Phase 4: Monitoring & Iteration

- [ ] Check workflow runs in GitHub Actions
- [ ] Monitor Slack notifications for failures
- [ ] Adjust platform-specific text as needed via `social_overrides`

## Known Limitations & Future Work

| Item | Status | Notes |
|------|--------|-------|
| Instagram posting | ❌ Not implemented | Requires image extraction + Graph API |
| Facebook posting | ⚠️ Partial | Config exists; implementation pending |
| LinkedIn image upload | ❌ Not implemented | Can only post text + link today |
| Cross-posting conflicts | ✅ Designed | `mention_brands` field prevents tag spam |
| Post scheduling | ❌ Not implemented | Workflow triggers on push; no deferred publishing |
| Metrics/analytics | ❌ Not implemented | Consider adding post link tracking |
| Retry logic | ⚠️ Partial | `continue-on-error: true` per platform; no backoff |

## Testing Locally

Run the Python scripts locally with mock data:

```bash
# Test post parsing
python3 << 'EOF'
import yaml
from pathlib import Path
from datetime import datetime

post_path = "brands/dlockamy/posts/2026-08-01-test.md"
with open(post_path) as f:
    content = f.read()

import re
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if match:
    fm = yaml.safe_load(match.group(1))
    print(f"Title: {fm.get('title')}")
    print(f"Brands: {fm.get('brands', [])}")
    print(f"Date: {fm.get('date')}")
EOF

# Test config loading
python3 << 'EOF'
import yaml

with open('.github/social-config.yml') as f:
    config = yaml.safe_load(f)

for brand, cfg in config['brands'].items():
    enabled_platforms = [p for p, c in cfg['platforms'].items() if c.get('enabled')]
    print(f"{brand}: {', '.join(enabled_platforms)}")
EOF
```

## Debugging

### Workflow run failed silently

Check GitHub Actions UI for step-by-step output. Common issues:

1. **Missing secrets**: Verify all `SOCIAL_CREDS_*` exist and are valid JSON
2. **Invalid credentials**: Test API keys directly via SDK docs
3. **Post file not found**: Workflow detects by path glob; verify naming
4. **Frontmatter parse error**: YAML syntax must be valid; use a YAML linter

### A post posted to some platforms but not others

This is expected — each platform step has `continue-on-error: true`. Check logs for platform-specific errors.

### Slack notification didn't send

1. Verify `SLACK_WEBHOOK_URL` is correct (should start with `https://hooks.slack.com`)
2. Check webhook is still active in Slack app settings
3. Review action logs for HTTP errors

## Next Steps

1. **Operationalize**: Create initial `.github/social-config.yml` and brand metadata
2. **Ingest existing posts**: Move blog archive into `brands/*/posts/` with proper frontmatter
3. **Generate credentials**: Mint API keys and OAuth tokens per platform
4. **Test on staging**: Create feature branch with test post, run workflow, verify output
5. **Go live**: Merge to main, configure Slack alerts, monitor for 48 hours

---

**Design Philosophy**: Configuration-driven routing allows each brand to own its own voice and social strategy without code changes. Posts declare which brands they target; the workflow handles the rest. Future brands can be added by extending `.github/social-config.yml` and creating a new `brands/*/` directory.
