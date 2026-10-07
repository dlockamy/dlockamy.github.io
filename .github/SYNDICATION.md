# Cross-posting new blog posts

When a new post is pushed to `master`, a GitHub Action can share it to **LinkedIn**, **Bluesky** and **X**.
It supersedes the three-brand design in `MULTI_BRAND_SOCIAL_DESIGN.md` for this site: one blog, one
author, no `brands/` folder, no migration of existing posts.

**Status:** built and tested offline; **not yet run against the live APIs**, and no credentials are set,
so today every platform skips itself with a warning. Follow "Turning it on" below.

## Opting a post in

Nothing is posted unless the post asks for it, in its front matter:

```yaml
syndicate: true                      # every platform that has credentials
syndicate: [linkedin, bluesky]       # or just these (x, or twitter, also works)
social:                              # optional: your own wording per platform
  linkedin: "Text for LinkedIn"
  bluesky: "Text for Bluesky (300 characters)"
  x: "Text for X (the link is added for you)"
```

Only **new** files in `_posts/` trigger it. Editing an old post never re-posts it.
If a post has `ai_assisted: true`, each platform's text ends with "Drafted with AI assistance."
To drop that line, set the repository variable `SYNDICATE_DISCLOSE_AI` to `0`.

Preview exactly what a post will say, with lengths, before you push:

```
python3 -m venv /tmp/v && /tmp/v/bin/pip install -r .github/syndicate/requirements.txt
/tmp/v/bin/python .github/syndicate/syndicate.py preview --post _posts/2026-10-05-some-post.md
```

## What happens on a push

1. **detect** finds `_posts/` files added by the push that opt in, and builds one job per post and platform.
2. Each **post** job waits (up to 15 minutes) for the page to be live on dlockamy.com, so nothing links to a
   404 or to a build that failed, then posts.
3. A platform with no credentials is skipped with a warning. A failed platform shows a red job and the other
   platforms are unaffected: open the run and use **Re-run failed jobs**. Re-running only repeats the failed one.

Retries: a rate limit (429) is retried after the time the platform asks for. A rejected credential (401/403) is
**never** retried. A server error or timeout is **not** retried either, because the post may already exist; check
the platform, then re-run if it did not land. (Learned the hard way from the 2026-10-06 Jenkins lockout.)

Run it by hand from the Actions tab: **Syndicate new posts → Run workflow**, give a post path, leave **Dry run**
ticked to see the exact text and payload, untick it to post for real.

## Turning it on (the credentials)

Set each secret with `gh secret set NAME --repo dlockamy/dlockamy.github.io` (it prompts for the value, so it
never enters your shell history). Do **Bluesky** first: it is the simplest and a good first live test.

### Bluesky (free, no expiry)
1. bsky.app → Settings → Privacy and security → **App passwords** → add one, named `dlockamy-blog`.
2. Secrets: `BLUESKY_HANDLE` (e.g. `dlockamy.com` or `you.bsky.social`) and `BLUESKY_APP_PASSWORD`.
   An app password is not your account password and can be revoked on its own.

### LinkedIn (free, **re-authorize about every 60 days**)
1. linkedin.com/developers/apps → **Create app**. LinkedIn asks for a Company Page to associate it with; a
   minimal page works.
2. App → **Products** tab → request **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect**.
3. App → **Auth** tab → under *Authorized redirect URLs for your app* add `http://localhost:8765/callback`.
   Copy the **Client ID** and **Client Secret**.
4. On your own machine: `python3 .github/syndicate/linkedin_auth.py --client-id <the id>`.
   It asks for the client secret (hidden), opens LinkedIn's consent page, then stores `LINKEDIN_ACCESS_TOKEN`,
   `LINKEDIN_PERSON_URN`, `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` as repo secrets itself. The token is
   never printed or written to disk.
5. **Why every 60 days:** LinkedIn gives refresh tokens only to approved partners
   ([their docs](https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens)),
   so a self-serve app's token simply expires. The **Syndication token check** workflow runs weekly and opens an
   issue (label `syndication-token`) when under 14 days remain. Fix: run step 4 again.
6. LinkedIn retires API versions about a year after release. If posts start failing with 426, set the repository
   variable `LINKEDIN_VERSION` to a current `YYYYMM` (the default is `202609`).

### X (costs money, **pay per post**)
1. X developer console → create a project and app. Set the app's permission to **Read and Write**.
2. Generate **API Key / Secret** and **Access Token / Secret** *after* setting Read and Write (tokens made
   before the change stay read-only; regenerate them).
3. The API has no free tier for new developers. It is pay-per-use: buy credits in the console. Third-party
   pricing pages (checked 2026-10-06, **verify in the console**) put a post at about $0.015, or about **$0.20 when
   it contains a link**, which every one of these does. Roughly $1 a month at one post a week.
4. Secrets: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`.
   The weekly check never calls X, because every call spends credits.

### First live test, in this order
1. Actions → **Syndicate new posts** → Run workflow, an old post, `platforms: bluesky`, **Dry run on**. Read the log.
2. Same again with Dry run off, `platforms: bluesky`. Look at the result on Bluesky.
3. Repeat for `linkedin`, then `x`.
4. Add `syndicate: true` to the next real post.

## Known unknowns (honest list)
Everything is tested against fakes that mirror each platform's documented request shape. Not yet confirmed
against the live services: LinkedIn API version `202609` and its title/description length limits (set
conservatively), the X host `api.x.com`, and a LinkedIn link card without a thumbnail image (the Posts API does
not scrape the URL, so the card is text only; adding a thumbnail needs LinkedIn's Images API).

## Files
`workflows/syndicate.yml` posts. `workflows/syndicate-token-check.yml` weekly health check.
`workflows/syndicate-tests.yml` runs the tests on changes. `syndicate/syndicate.py` the script,
`syndicate/linkedin_auth.py` the LinkedIn authorization helper, `syndicate/test_syndicate.py` the tests.
Everything is under `.github/`, which Jekyll does not publish.
