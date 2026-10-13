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
- **Cross-posting (opt-in):** add `syndicate: true` (or a list of `linkedin`, `bluesky`, `mastodon`) to a post's front matter to have the push share it. Nothing posts without it. See `.github/SYNDICATION.md`.
- Images live in `images/`; the CSS keeps them inside the column (`.post__content img { max-width: 100% }`). **Look at the rendered page before publishing.**
- Build check: `docker build -t dlockamy-site .` then `docker run --rm -v "$PWD":/site -v /tmp/out:/out dlockamy-site bundle exec jekyll build -d /out` (restore `Gemfile.lock` afterwards: the container rewrites it).
- Never publish secrets, IPs, internal hostnames beyond what earlier posts already use, private repo names, or anything the post cannot trace to a source.

## Analytics (2026-10-12)

- **Cloudflare Web Analytics**, cookieless, page views and referrers only. The beacon `<script>` is in `_layouts/default.html`, rendered only when `jekyll.environment == "production"` (GitHub Pages' legacy builder sets that; a local `jekyll build` does not, so previews carry no beacon). The beacon token in the layout is public by design.
- The Web Analytics site for `dlockamy.com` has existed since 2026-08-01 with `auto_install: true`, but Cloudflare was **not** injecting the beacon into the pages, so the layout carries it explicitly. Cloudflare does not double-inject (one beacon per page was confirmed on the live site).
- Dashboard: Cloudflare, account Web Analytics. The account-owned API token `cloudflare_api_token` (AWS Secrets Manager `sol/softsurve`) can list the Web Analytics sites and read zone settings; it was only read, never changed.
- Cross-posted links carry `?utm_source=<platform>&utm_medium=social` (`.github/syndicate/syndicate.py`, `link()`); the post's own URL and the idempotency key stay untagged. Cloudflare Web Analytics may not break traffic out by those tags and apps often strip the referrer; GoatCounter (free for non-commercial use) or Plausible would show per-platform numbers if that matters.

## Known issues (2026-10-12)

- **GitHub Pages' origin certificate** for `dlockamy.com` and `www` is in state `bad_authz` and expires 2026-10-18 (Let's Encrypt, so GitHub cannot renew it). **Visitors are not affected**: Cloudflare terminates TLS with its own certificate (Google Trust Services, auto-renewing, valid to 2026-12-28) and the zone's SSL mode is `full`, which does not validate the origin certificate. The ACME challenge path is reachable through Cloudflare (a probe returns GitHub's 404 over plain HTTP, no redirect), and re-saving the same custom domain through the API (2026-10-13) did not clear the state. The reliable fix is removing and re-adding the custom domain, which briefly un-serves the site and opens a small window in which another GitHub user could claim the domain (it is not a verified domain); do it after adding domain verification (a `_github-pages-challenge-dlockamy` TXT record) and not before.
- **Dependabot:** the four alerts (concurrent-ruby x3 including one high, json x1) were fixed on 2026-10-13 by bumping `Gemfile.lock` (PR #12); all alerts are now closed.
- The first live cross-post (2026-10-11) ran green on LinkedIn, Bluesky and Mastodon in Actions; LinkedIn's API version and link card remain unconfirmed against the live service.
- Previewing an unpublished post: `jekyll build --unpublished` (a post with `published: false` is skipped otherwise). The chart for the 2026-10-11 post came from a script kept in the vault under `wiki/experiments/assets/ai-kit-wrap-up-helpers/`.
