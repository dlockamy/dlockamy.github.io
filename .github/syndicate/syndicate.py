#!/usr/bin/env python3
"""Cross-post NEW dlockamy.com blog posts to LinkedIn, Bluesky and X.

Opt-in per post, in the post's front matter:

    syndicate: true                      # every platform that has credentials
    syndicate: [linkedin, bluesky]       # only these
    social:                              # optional per-platform text override
      linkedin: "Custom commentary"

A post with no `syndicate:` key is never posted. Only files ADDED under
`_posts/` trigger a post, so editing an old post does not re-post it.

Sub-commands
    detect        which (post, platform) pairs a push should post  -> JSON matrix
    post          post one post to one platform (or --dry-run it)
    preview       show the text each platform would get, with its length
    check-tokens  report credential health (LinkedIn token expiry, Bluesky login)

Design rules, from the 2026-10-06 Jenkins/Keycloak lockout:
  * A rejected credential (401/403) is TERMINAL. Never retried.
  * Retry only when the request provably did not land: 429 (honouring
    Retry-After) and connection errors before any response. A 5xx or a timeout
    after sending is ambiguous (the post may exist), so it is NOT retried; re-run
    the failed job by hand instead.
  * No credential value is ever printed, logged or put in an error message.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

SITE_URL = os.environ.get("SYNDICATE_SITE_URL", "https://dlockamy.com").rstrip("/")
PLATFORMS = ("linkedin", "bluesky", "x")
ALIASES = {"twitter": "x"}

# LinkedIn rotates API versions (YYYYMM) and sunsets old ones after about a year.
# Override with the LINKEDIN_VERSION repository variable; a 426 means this one is gone.
LINKEDIN_VERSION_DEFAULT = "202609"
LINKEDIN_API = "https://api.linkedin.com"
BLUESKY_PDS_DEFAULT = "https://bsky.social"
X_API_DEFAULT = "https://api.x.com"

# Limits. LinkedIn's title/description caps are not documented where we read, so
# these are deliberately conservative.
LINKEDIN_COMMENTARY_MAX = 3000
LINKEDIN_TITLE_MAX = 190
LINKEDIN_DESC_MAX = 250
BLUESKY_TEXT_MAX = 300  # graphemes; counting code points is a safe upper bound
X_TEXT_MAX = 280  # weighted; a URL always counts 23
X_URL_WEIGHT = 23

AI_NOTE_DEFAULT = "Drafted with AI assistance."


_SECRET_KEYS = (
    "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_CLIENT_SECRET", "BLUESKY_APP_PASSWORD",
    "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "X_API_KEY",
)


def redact(text: str, env) -> str:
    """Belt and braces: a platform's error body must never carry one of our secrets into a log."""
    for k in _SECRET_KEYS:
        v = env.get(k) if env is not None else None
        if v and len(v) >= 4:
            text = text.replace(v, "***")
    return text


class PostError(Exception):
    """A platform call failed. The message is already credential-free."""

    def __init__(self, message: str, *, terminal: bool = True):
        super().__init__(message)
        self.terminal = terminal


# --------------------------------------------------------------------------- posts


@dataclass
class Post:
    path: str
    title: str
    date: dt.date
    excerpt: str
    ai_assisted: bool
    syndicate: Optional[set]  # None = not opted in
    overrides: dict = field(default_factory=dict)
    url: str = ""


_FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", re.S)


def _slugify(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", s).strip("-").lower()


def _plain(md: str) -> str:
    """Markdown -> one line of plain text (good enough for an excerpt).

    Only removes markup. Underscores inside words (qr_glue_http), `#` in C#, and a
    lone `*` are text and are kept; the per-platform escaping handles them later.
    """
    s = re.sub(r"```.*?```", " ", md, flags=re.S)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)  # images
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)  # links -> their text
    s = re.sub(r"<[^>]+>", " ", s)  # html tags
    s = s.replace("`", "")
    s = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", s)  # bold
    s = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"\1", s)  # *emphasis*
    s = re.sub(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])", r"\1", s)  # _emphasis_ (not intraword)
    s = re.sub(r"(?m)^\s{0,3}(#{1,6}\s+|>\s?)", "", s)  # heading / quote markers at line start
    return re.sub(r"\s+", " ", s).strip()


def normalise_syndicate(value: Any) -> Optional[set]:
    """`true` -> all platforms, a list -> those, false/absent -> None."""
    if value is None or value is False:
        return None
    if value is True:
        return set(PLATFORMS)
    if isinstance(value, str):
        value = [v for v in re.split(r"[,\s]+", value) if v]
    chosen = set()
    for v in value:
        name = ALIASES.get(str(v).strip().lower(), str(v).strip().lower())
        if name not in PLATFORMS:
            raise ValueError(f"unknown syndication platform {v!r} (known: {', '.join(PLATFORMS)})")
        chosen.add(name)
    return chosen or None


def parse_post(path: str, text: Optional[str] = None) -> Post:
    import yaml

    if text is None:
        text = Path(path).read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        raise ValueError(f"{path}: no front matter")
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    name = Path(path).name
    fn = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+?)\.(?:md|markdown)$", name)
    if not fn:
        raise ValueError(f"{path}: filename is not YYYY-MM-DD-slug.md")
    file_date = dt.date(int(fn.group(1)), int(fn.group(2)), int(fn.group(3)))

    # Jekyll: a front-matter `date` overrides the filename date, URL included.
    fm_date = fm.get("date")
    if isinstance(fm_date, dt.datetime):
        date = fm_date.date()
    elif isinstance(fm_date, dt.date):
        date = fm_date
    elif isinstance(fm_date, str):
        date = dt.date.fromisoformat(fm_date[:10])
    else:
        date = file_date

    title = str(fm.get("title") or "").strip()
    if not title:
        raise ValueError(f"{path}: no title")

    excerpt = _plain(str(fm.get("excerpt") or ""))
    if not excerpt:
        first = next((p for p in re.split(r"\n\s*\n", body) if _plain(p)), "")
        excerpt = _plain(first)

    return Post(
        path=path,
        title=title,
        date=date,
        excerpt=excerpt,
        ai_assisted=bool(fm.get("ai_assisted")),
        syndicate=normalise_syndicate(fm.get("syndicate")),
        overrides={ALIASES.get(k, k): str(v) for k, v in (fm.get("social") or {}).items()},
        url=f"{SITE_URL}/posts/{date.year:04d}/{date.month:02d}/{date.day:02d}/{_slugify(fn.group(4))}/",
    )


# ------------------------------------------------------------------------ text utils


def truncate(text: str, limit: int, ellipsis: str = "…") -> str:
    """Cut at a word boundary to at most `limit` code points."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[: max(limit - len(ellipsis), 0)]
    if " " in cut and not text[len(cut)].isspace():
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.-") + ellipsis


_LITTLE_RESERVED = set("|{}@[]()<>#\\*_~")


def escape_little(text: str) -> str:
    """LinkedIn's `little` text format reserves these; unescaped they truncate or garble a post."""
    return "".join("\\" + c if c in _LITTLE_RESERVED else c for c in text)


def x_weight(text: str) -> int:
    """X's weighted length: most Latin text is 1, everything else (CJK, emoji) is 2."""
    w = 0
    for c in text:
        cp = ord(c)
        w += 1 if (cp <= 0x10FF or 0x2000 <= cp <= 0x200D or 0x2010 <= cp <= 0x201F or 0x2032 <= cp <= 0x2037) else 2
    return w


def _ai_note(p: Post) -> str:
    if p.ai_assisted and os.environ.get("SYNDICATE_DISCLOSE_AI", "1") not in ("0", "false", "no"):
        return os.environ.get("SYNDICATE_AI_NOTE", AI_NOTE_DEFAULT)
    return ""


# ---------------------------------------------------------------------------- compose


def compose_linkedin(p: Post, author_urn: str = "urn:li:person:EXAMPLE") -> dict:
    if "linkedin" in p.overrides:
        commentary = p.overrides["linkedin"]
    else:
        parts = [p.excerpt or p.title]
        note = _ai_note(p)
        if note:
            parts.append(note)
        commentary = "\n\n".join(parts)
    commentary = truncate(commentary, LINKEDIN_COMMENTARY_MAX // 2)  # headroom for escapes
    commentary = escape_little(commentary)
    return {
        "author": author_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        # The Posts API does NOT scrape the URL; the card's text must be supplied.
        "content": {
            "article": {
                "source": p.url,
                "title": truncate(p.title, LINKEDIN_TITLE_MAX),
                "description": truncate(p.excerpt or p.title, LINKEDIN_DESC_MAX),
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }


def compose_bluesky_text(p: Post) -> str:
    if "bluesky" in p.overrides:
        return truncate(p.overrides["bluesky"], BLUESKY_TEXT_MAX)
    note = _ai_note(p)
    tail = f"\n\n{note}" if note else ""
    head = p.title if not p.excerpt else f"{p.title}\n\n{p.excerpt}"
    room = BLUESKY_TEXT_MAX - len(tail)
    text = truncate(head, room) + tail
    return text if len(text) <= BLUESKY_TEXT_MAX else truncate(head, BLUESKY_TEXT_MAX)


def compose_bluesky_record(p: Post, now: Optional[dt.datetime] = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    return {
        "$type": "app.bsky.feed.post",
        "text": compose_bluesky_text(p),
        "createdAt": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        "langs": ["en"],
        "embed": {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": p.url,
                "title": truncate(p.title, 300),
                "description": truncate(p.excerpt or p.title, 300),
            },
        },
    }


def compose_x_text(p: Post) -> str:
    """Title, then as much excerpt as fits, then the AI note (if on), then the URL (always 23)."""
    if "x" in p.overrides:
        body = p.overrides["x"]
        return body if p.url in body else f"{body}\n{p.url}"
    note = _ai_note(p)
    tail = f"\n\n{note}" if note else ""
    budget = X_TEXT_MAX - X_URL_WEIGHT - 1 - x_weight(tail)  # 1 = the newline before the URL
    text = p.title
    if x_weight(text) > budget:
        text = truncate(p.title, budget // 2)
        while x_weight(text) > budget:
            text = truncate(text, len(text) - 2)
    elif p.excerpt:
        extra_budget = budget - x_weight(text) - 2  # blank line between title and excerpt
        if extra_budget > 40:
            extra = truncate(p.excerpt, extra_budget)
            while x_weight(extra) > extra_budget and len(extra) > 1:
                extra = truncate(extra, len(extra) - 2)
            text = f"{text}\n\n{extra}"
    return f"{text}{tail}\n{p.url}"


def x_text_weight(text: str, url: str) -> int:
    return x_weight(text.replace(url, "")) + (X_URL_WEIGHT if url in text else 0)


# ------------------------------------------------------------------------------ http


class Http:
    """Thin wrapper so tests can inject a fake. Never logs request headers or bodies."""

    def __init__(self):
        import requests

        self._r = requests
        self.timeout = 30

    def post(self, url, **kw):
        return self._r.post(url, timeout=self.timeout, **kw)

    def get(self, url, **kw):
        return self._r.get(url, timeout=self.timeout, **kw)


def _snippet(resp) -> str:
    try:
        body = resp.text or ""
    except Exception:
        body = ""
    return re.sub(r"\s+", " ", body)[:300]


def _send(http, method: str, url: str, *, retries: int = 2, sleep: Callable = time.sleep, **kw):
    """One request; retry ONLY when it provably did not land (429, connect error)."""
    import requests

    for attempt in range(retries + 1):
        try:
            resp = getattr(http, method)(url, **kw)
        except requests.exceptions.ConnectionError as e:
            if attempt < retries:
                sleep(2 * (attempt + 1))
                continue
            raise PostError(f"could not connect to {url.split('/')[2]}: {type(e).__name__}", terminal=False)
        except requests.exceptions.RequestException as e:
            # Timeout after sending is ambiguous: the post may exist. Do not retry.
            raise PostError(f"{type(e).__name__} calling {url.split('/')[2]}; NOT retried, the post may exist", terminal=True)
        if resp.status_code == 429 and attempt < retries:
            wait = 60
            try:
                wait = min(int(resp.headers.get("Retry-After", wait)), 300)
            except ValueError:
                pass
            sleep(wait)
            continue
        return resp
    raise AssertionError("unreachable")


# ---------------------------------------------------------------------------- clients


def post_linkedin(p: Post, env, http, sleep=time.sleep) -> str:
    token, author = env["LINKEDIN_ACCESS_TOKEN"], env["LINKEDIN_PERSON_URN"]
    version = env.get("LINKEDIN_VERSION") or LINKEDIN_VERSION_DEFAULT
    resp = _send(
        http, "post", f"{LINKEDIN_API}/rest/posts", sleep=sleep,
        headers={
            "Authorization": f"Bearer {token}",
            "Linkedin-Version": version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json=compose_linkedin(p, author),
    )
    if resp.status_code == 201:
        return resp.headers.get("x-restli-id", "(created; no id returned)")
    hint = {
        401: "the access token is expired or revoked: re-run linkedin_auth.py (tokens last 60 days)",
        403: "the token lacks w_member_social, or the app lacks the 'Share on LinkedIn' product",
        426: f"API version {version} is no longer supported: set the LINKEDIN_VERSION repository variable to a current YYYYMM",
        422: "LinkedIn rejected the post content",
    }.get(resp.status_code, "")
    raise PostError(redact(f"LinkedIn HTTP {resp.status_code}: {hint or _snippet(resp)}", env))


def post_bluesky(p: Post, env, http, sleep=time.sleep) -> str:
    pds = (env.get("BLUESKY_PDS") or BLUESKY_PDS_DEFAULT).rstrip("/")
    s = _send(http, "post", f"{pds}/xrpc/com.atproto.server.createSession", sleep=sleep,
              json={"identifier": env["BLUESKY_HANDLE"], "password": env["BLUESKY_APP_PASSWORD"]})
    if s.status_code != 200:
        raise PostError(redact(f"Bluesky login HTTP {s.status_code}: is the app password valid? ({_snippet(s)})", env))
    sess = s.json()
    r = _send(http, "post", f"{pds}/xrpc/com.atproto.repo.createRecord", sleep=sleep,
              headers={"Authorization": f"Bearer {sess['accessJwt']}"},
              json={"repo": sess["did"], "collection": "app.bsky.feed.post", "record": compose_bluesky_record(p)})
    if r.status_code != 200:
        raise PostError(redact(f"Bluesky createRecord HTTP {r.status_code}: {_snippet(r)}", env))
    return r.json().get("uri", "(created)")


def post_x(p: Post, env, http, sleep=time.sleep) -> str:
    from requests_oauthlib import OAuth1

    text = compose_x_text(p)
    if x_text_weight(text, p.url) > X_TEXT_MAX:
        raise PostError(f"X text is {x_text_weight(text, p.url)} weighted characters, over {X_TEXT_MAX}")
    auth = OAuth1(env["X_API_KEY"], env["X_API_SECRET"], env["X_ACCESS_TOKEN"], env["X_ACCESS_SECRET"])
    base = (env.get("X_API_BASE") or X_API_DEFAULT).rstrip("/")
    resp = _send(http, "post", f"{base}/2/tweets", sleep=sleep, auth=auth, json={"text": text})
    if resp.status_code in (200, 201):
        return (resp.json().get("data") or {}).get("id", "(created)")
    hint = {
        401: "X rejected the keys: check the four X_* secrets and that the app has Read and Write permission",
        402: "X reports no API credits: top up in the developer console (the API is pay-per-use)",
        403: "X refused the post: app permissions, a duplicate post, or no credits",
    }.get(resp.status_code, "")
    raise PostError(redact(f"X HTTP {resp.status_code}: {hint or _snippet(resp)}", env))


CLIENTS = {"linkedin": post_linkedin, "bluesky": post_bluesky, "x": post_x}
REQUIRED = {
    "linkedin": ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN"),
    "bluesky": ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"),
    "x": ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"),
}


def missing_credentials(platform: str, env) -> list:
    return [k for k in REQUIRED[platform] if not env.get(k)]


# --------------------------------------------------------------------------- commands


def added_posts(before: str, after: str, repo: str = ".") -> list:
    """`_posts/` files ADDED between two commits (edits to old posts are ignored)."""
    if not before or set(before) == {"0"}:  # first push to a branch
        cmd = ["git", "show", "--name-status", "--diff-filter=A", "--format=", after]
    else:
        cmd = ["git", "diff", "--name-status", "--diff-filter=A", before, after, "--", "_posts"]
    out = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=True).stdout
    files = []
    for line in out.splitlines():
        status, _, path = line.partition("\t")
        if status == "A" and path.startswith("_posts/") and path.endswith((".md", ".markdown")):
            files.append(path)
    return sorted(files)


def build_matrix(paths: list, repo: str = ".", platforms: Optional[set] = None, force: bool = False) -> dict:
    include = []
    for path in paths:
        p = parse_post(str(Path(repo) / path))
        p.path = path
        chosen = p.syndicate if p.syndicate is not None else (set(PLATFORMS) if force else None)
        if chosen is None:
            continue
        if platforms:
            chosen = chosen & platforms
        for plat in PLATFORMS:
            if plat in chosen:
                include.append({"post": path, "platform": plat, "title": p.title})
    return {"include": include}


def wait_live(url: str, http, timeout: int = 900, interval: int = 20, sleep=time.sleep, clock=time.monotonic) -> bool:
    """A post is pushed before Pages has built it. Do not link to a 404 (or to a build that failed)."""
    deadline = clock() + timeout
    while True:
        try:
            if http.get(url, headers={"User-Agent": "dlockamy-syndicate/1"}).status_code == 200:
                return True
        except Exception:
            pass
        if clock() >= deadline:
            return False
        sleep(interval)


def summary(line: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def cmd_detect(a) -> int:
    if a.post:
        paths = [a.post]
        plats = {ALIASES.get(x.strip(), x.strip()) for x in a.platforms.split(",") if x.strip()} or None
        matrix = build_matrix(paths, platforms=plats, force=True)
    else:
        matrix = build_matrix(added_posts(a.before, a.after))
    any_ = bool(matrix["include"])
    print(json.dumps(matrix))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"matrix={json.dumps(matrix)}\nany={'true' if any_ else 'false'}\n")
    return 0


def cmd_post(a, env=None, http=None, sleep=time.sleep, clock=time.monotonic) -> int:
    env = os.environ if env is None else env
    p = parse_post(a.post)
    platform = ALIASES.get(a.platform, a.platform)
    if platform not in PLATFORMS:
        print(f"unknown platform {a.platform!r}", file=sys.stderr)
        return 2
    if a.dry_run:
        print(f"[dry run] {platform} <- {p.url}")
        print(json.dumps(_preview_payload(p, platform), indent=2, ensure_ascii=False))
        summary(f"- {platform}: dry run, nothing posted ({p.title})")
        return 0
    miss = missing_credentials(platform, env)
    if miss:
        print(f"::warning::{platform} skipped: missing secret(s) {', '.join(miss)}")
        summary(f"- {platform}: **skipped**, secrets not set ({', '.join(miss)})")
        return 0
    http = http or Http()
    if a.wait_live and not wait_live(p.url, http, timeout=a.wait_live, sleep=sleep, clock=clock):
        print(f"::error::{p.url} is not live after {a.wait_live}s (did the Pages build fail?). Nothing was posted.")
        summary(f"- {platform}: **not posted**, {p.url} never went live")
        return 1
    try:
        ident = CLIENTS[platform](p, env, http, sleep=sleep)
    except PostError as e:
        print(f"::error::{platform}: {e}")
        summary(f"- {platform}: **FAILED**: {e}")
        return 1
    print(f"posted to {platform}: {ident}")
    summary(f"- {platform}: posted ({ident}) <- {p.url}")
    return 0


def _preview_payload(p: Post, platform: str) -> dict:
    if platform == "linkedin":
        return compose_linkedin(p)
    if platform == "bluesky":
        return compose_bluesky_record(p)
    text = compose_x_text(p)
    return {"text": text, "weighted_length": x_text_weight(text, p.url), "limit": X_TEXT_MAX}


def cmd_preview(a) -> int:
    p = parse_post(a.post)
    print(f"{p.title}\n{p.url}\nopted in: {sorted(p.syndicate) if p.syndicate else 'NO (no syndicate: key)'}\n")
    li = compose_linkedin(p)
    print(f"--- LinkedIn commentary ({len(li['commentary'])}/{LINKEDIN_COMMENTARY_MAX})\n{li['commentary']}")
    print(f"    card: {li['content']['article']['title']!r} / {li['content']['article']['description']!r}")
    bt = compose_bluesky_text(p)
    print(f"\n--- Bluesky ({len(bt)}/{BLUESKY_TEXT_MAX})\n{bt}")
    xt = compose_x_text(p)
    print(f"\n--- X ({x_text_weight(xt, p.url)}/{X_TEXT_MAX} weighted)\n{xt}")
    return 0


def linkedin_days_left(env, http) -> Optional[float]:
    r = http.post(
        "https://www.linkedin.com/oauth/v2/introspectToken",
        data={"client_id": env["LINKEDIN_CLIENT_ID"], "client_secret": env["LINKEDIN_CLIENT_SECRET"],
              "token": env["LINKEDIN_ACCESS_TOKEN"]},
    )
    if r.status_code != 200:
        raise PostError(redact(f"LinkedIn introspection HTTP {r.status_code}: {_snippet(r)}", env))
    j = r.json()
    if not j.get("active"):
        return 0.0
    return max((int(j["expires_at"]) - time.time()) / 86400, 0.0)


def cmd_check_tokens(a, env=None, http=None) -> int:
    """Exit 2 when something needs a human: a token near expiry, or a login that no longer works."""
    env = os.environ if env is None else env
    http = http or Http()
    problems, lines = [], []
    li_keys = ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET")
    if all(env.get(k) for k in li_keys):
        try:
            days = linkedin_days_left(env, http)
            if days is None or days <= 0:
                problems.append("LinkedIn access token is expired or revoked. Run linkedin_auth.py.")
                lines.append("linkedin: EXPIRED")
            elif days < a.warn_days:
                problems.append(f"LinkedIn access token expires in {days:.0f} days. Run linkedin_auth.py before then.")
                lines.append(f"linkedin: {days:.0f} days left (WARN)")
            else:
                lines.append(f"linkedin: {days:.0f} days left")
        except PostError as e:
            problems.append(f"Could not check the LinkedIn token: {e}")
            lines.append("linkedin: check failed")
    else:
        lines.append("linkedin: not configured")
    if all(env.get(k) for k in REQUIRED["bluesky"]):
        pds = (env.get("BLUESKY_PDS") or BLUESKY_PDS_DEFAULT).rstrip("/")
        r = http.post(f"{pds}/xrpc/com.atproto.server.createSession",
                      json={"identifier": env["BLUESKY_HANDLE"], "password": env["BLUESKY_APP_PASSWORD"]})
        if r.status_code == 200:
            lines.append("bluesky: login ok")
        else:
            problems.append(f"Bluesky login failed (HTTP {r.status_code}): the app password may have been revoked.")
            lines.append("bluesky: LOGIN FAILED")
    else:
        lines.append("bluesky: not configured")
    lines.append("x: not checked (any call spends pay-per-use credits)")
    print("\n".join(lines))
    for ln in lines:
        summary(f"- {ln}")
    if problems:
        report = "\n".join(f"- {x}" for x in problems)
        print("\nNEEDS ATTENTION:\n" + report)
        if a.report:
            Path(a.report).write_text(report + "\n")
        return 2
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect")
    d.add_argument("--before", default="")
    d.add_argument("--after", default="HEAD")
    d.add_argument("--post", help="explicit post path (manual run); bypasses 'added in this push'")
    d.add_argument("--platforms", default="", help="comma list for a manual run (blank = every platform)")
    po = sub.add_parser("post")
    po.add_argument("--post", required=True)
    po.add_argument("--platform", required=True)
    po.add_argument("--dry-run", action="store_true")
    po.add_argument("--wait-live", type=int, default=0, metavar="SECONDS")
    pr = sub.add_parser("preview")
    pr.add_argument("--post", required=True)
    ck = sub.add_parser("check-tokens")
    ck.add_argument("--warn-days", type=int, default=14)
    ck.add_argument("--report", help="write the problems to this file")
    a = ap.parse_args(argv)
    return {"detect": cmd_detect, "post": cmd_post, "preview": cmd_preview, "check-tokens": cmd_check_tokens}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
