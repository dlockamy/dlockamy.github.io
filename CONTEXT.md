# Context — dlockamy/dlockamy.github.io
# Douglas Lockamy personal portfolio · LS project

**What it is:** Personal portfolio site for Douglas Lockamy (DJ).
Live at dlockamy.com. Built with Jekyll.

**Theme:** Mission Console — retro-futurist IBM mainframe aesthetic.
Teal phosphor on dark, Orbitron + IBM Plex Mono, live GitHub API integration.
Distinct from Digital Zen — this site has its own standalone visual identity.

**Stack:** Jekyll 4.3, GitHub Pages (or self-hosted).
**CI:** Jenkinsfile → Jekyll build → archive `_site/`. Publishes gem if gemspec exists.
**Jira:** LS project (new work). Legacy: KAN-4, KAN-32–34.

**Design notes:** The Mission Console theme is deliberately retro and personal —
not a template for Lockamy Studios products. Keep it separate from Digital Zen.

## Post conventions (kept short on purpose)

- **Titles are human-friendly and to the point** (DJ, 2026-10-05): about 3 to 8 words, said the way a person would say them. No stacked clauses, lists, or run-ons; plain over clever. Do not reuse the title as a section heading in the post.
- **Filename and slug:** `_posts/YYYY-MM-DD-<short-slug>.md`, 3 to 6 words. **Never change the slug of a published post** (links, the feed and shared URLs depend on it); retitle only.
- Front matter: `layout: post`, `title`, `date`, `categories`, `tags`, `excerpt`, `author: Douglas Lockamy`, `ai_assisted: true` when an agent drafted it.
- **Cross-posting (opt-in):** add `syndicate: true` (or a list of `linkedin`, `bluesky`, `x`) to a post's front matter to have the push share it. Nothing posts without it. See `.github/SYNDICATION.md`.
- Images live in `images/`; the CSS keeps them inside the column (`.post__content img { max-width: 100% }`). **Look at the rendered page before publishing.**
- Build check: `docker build -t dlockamy-site .` then `docker run --rm -v "$PWD":/site -v /tmp/out:/out dlockamy-site bundle exec jekyll build -d /out` (restore `Gemfile.lock` afterwards: the container rewrites it).
- Never publish secrets, IPs, internal hostnames beyond what earlier posts already use, private repo names, or anything the post cannot trace to a source.
