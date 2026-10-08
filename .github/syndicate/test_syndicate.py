"""Tests for syndicate.py. No network: every HTTP call goes through a recording fake."""
import datetime as dt
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import requests  # noqa: E402

import syndicate as s  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
_REAL_PARSE_POST = s.parse_post  # tests patch s.parse_post; helpers must use the real one

POST_TEXT = """---
layout: post
title: "Giving two generated characters a skeleton"
date: 2026-10-05
categories: [hardware]
tags: [3d]
excerpt: "I took two images through the same pipeline (measure, build, rig) and **both** worked_ok."
author: Douglas Lockamy
ai_assisted: true
syndicate: true
---

Body paragraph one.
"""


def mkpost(extra="", ai=True, title="Giving two generated characters a skeleton", excerpt="A short excerpt.", date="2026-10-05"):
    fm = f'---\nlayout: post\ntitle: "{title}"\ndate: {date}\nexcerpt: "{excerpt}"\nai_assisted: {str(ai).lower()}\n{extra}---\n\nBody.\n'
    return _REAL_PARSE_POST(f"_posts/{date}-a-test-post.md", text=fm)


class Resp:
    def __init__(self, status=200, body=None, headers=None, text=""):
        self.status_code = status
        self._body = body if body is not None else {}
        self.headers = headers or {}
        self.text = text or json.dumps(self._body)

    def json(self):
        return self._body


class FakeHttp:
    """Replays queued responses and records every request (url + kwargs)."""

    def __init__(self, *responses, default=None):
        self.queue = list(responses)
        self.default = default if default is not None else Resp(200)
        self.calls = []

    def _do(self, method, url, **kw):
        self.calls.append((method, url, kw))
        item = self.queue.pop(0) if self.queue else self.default
        if isinstance(item, Exception):
            raise item
        return item

    def post(self, url, **kw):
        return self._do("post", url, **kw)

    def get(self, url, **kw):
        return self._do("get", url, **kw)


NOSLEEP = lambda _s: None  # noqa: E731


class ParsingTests(unittest.TestCase):
    def test_front_matter_fields_and_url(self):
        p = s.parse_post("_posts/2026-10-05-giving-a-skeleton.md", text=POST_TEXT)
        self.assertEqual(p.title, "Giving two generated characters a skeleton")
        self.assertEqual(p.url, "https://dlockamy.com/posts/2026/10/05/giving-a-skeleton/")
        self.assertTrue(p.ai_assisted)
        self.assertEqual(p.syndicate, {"linkedin", "bluesky", "mastodon", "x"})

    def test_excerpt_markdown_is_flattened(self):
        p = s.parse_post("_posts/2026-10-05-x.md", text=POST_TEXT)
        self.assertEqual(p.excerpt, "I took two images through the same pipeline (measure, build, rig) and both worked_ok.")

    def test_excerpt_keeps_identifiers_and_symbols_that_are_text_not_markup(self):
        text = '---\ntitle: T\ndate: 2026-01-02\nexcerpt: "Fixed qr_glue_http in C# and 3 * 4 = 12, see `code` and _this_ one."\n---\nB\n'
        self.assertEqual(
            s.parse_post("_posts/2026-01-02-t.md", text=text).excerpt,
            "Fixed qr_glue_http in C# and 3 * 4 = 12, see code and this one.",
        )

    def test_excerpt_falls_back_to_first_paragraph(self):
        text = "---\ntitle: T\ndate: 2026-01-02\n---\n\nFirst [link](http://x) para.\n\nSecond.\n"
        self.assertEqual(s.parse_post("_posts/2026-01-02-t.md", text=text).excerpt, "First link para.")

    def test_front_matter_date_overrides_filename_like_jekyll(self):
        p = mkpost(date="2026-10-05")
        p2 = s.parse_post("_posts/2026-10-05-a.md", text="---\ntitle: T\ndate: 2026-10-07\n---\nB\n")
        self.assertIn("/2026/10/05/", p.url)
        self.assertIn("/2026/10/07/", p2.url)

    def test_syndicate_values(self):
        self.assertIsNone(mkpost().syndicate)
        self.assertIsNone(mkpost("syndicate: false\n").syndicate)
        self.assertEqual(mkpost("syndicate: [linkedin, twitter]\n").syndicate, {"linkedin", "x"})
        self.assertEqual(mkpost("syndicate: [mastodon]\n").syndicate, {"mastodon"})
        self.assertEqual(mkpost("syndicate: bluesky\n").syndicate, {"bluesky"})

    def test_unknown_platform_is_an_error_not_a_silent_skip(self):
        with self.assertRaises(ValueError):
            mkpost("syndicate: [myspace]\n")

    def test_every_real_post_parses_and_urls_are_unique(self):
        posts = [s.parse_post(f) for f in sorted(glob.glob(str(REPO / "_posts" / "*.md")))]
        self.assertGreater(len(posts), 10)
        self.assertEqual(len({p.url for p in posts}), len(posts))
        self.assertTrue(all(p.excerpt for p in posts))


class TextTests(unittest.TestCase):
    def test_escape_little_covers_every_reserved_character(self):
        for c in "|{}@[]()<>#\\*_~":
            self.assertEqual(s.escape_little(f"a{c}b"), f"a\\{c}b", c)
        self.assertEqual(s.escape_little("plain text, 1.5!"), "plain text, 1.5!")

    def test_truncate_stops_at_a_word_and_never_exceeds_the_limit(self):
        out = s.truncate("alpha beta gamma delta", 14)
        self.assertLessEqual(len(out), 14)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn("gam", out)
        self.assertEqual(s.truncate("short", 50), "short")

    def test_x_weight(self):
        self.assertEqual(s.x_weight("abc"), 3)
        self.assertEqual(s.x_weight("日本"), 4)
        self.assertEqual(s.x_weight("🙂"), 2)


class ComposeTests(unittest.TestCase):
    def test_linkedin_payload_shape(self):
        p = mkpost()
        j = s.compose_linkedin(p, "urn:li:person:abc")
        self.assertEqual(j["author"], "urn:li:person:abc")
        self.assertEqual(j["visibility"], "PUBLIC")
        self.assertEqual(j["lifecycleState"], "PUBLISHED")
        self.assertEqual(j["distribution"]["feedDistribution"], "MAIN_FEED")
        self.assertEqual(j["content"]["article"]["source"], p.url)
        self.assertEqual(j["content"]["article"]["title"], p.title)
        self.assertTrue(j["content"]["article"]["description"])
        self.assertIn("Drafted with AI assistance.", j["commentary"])

    def test_linkedin_commentary_is_escaped(self):
        import re
        p = mkpost(excerpt="Use (parens), #tags, a_b and @mentions [now]")
        c = s.compose_linkedin(p)["commentary"]
        for ch in "()#_@[]":
            self.assertIsNone(re.search(r"(?<!\\)" + re.escape(ch), c), f"unescaped {ch!r} in {c!r}")
        self.assertIn("\\(parens\\)", c)
        self.assertIn("a\\_b", c)  # the underscore is kept, then escaped

    def test_linkedin_stays_under_the_limit_even_with_heavy_escaping(self):
        p = mkpost(excerpt="(" * 4000)
        self.assertLessEqual(len(s.compose_linkedin(p)["commentary"]), s.LINKEDIN_COMMENTARY_MAX)

    def test_ai_note_can_be_turned_off(self):
        old = os.environ.get("SYNDICATE_DISCLOSE_AI")
        os.environ["SYNDICATE_DISCLOSE_AI"] = "0"
        try:
            self.assertNotIn("AI assistance", s.compose_linkedin(mkpost())["commentary"])
            self.assertNotIn("AI assistance", s.compose_bluesky_text(mkpost()))
            self.assertNotIn("AI assistance", s.compose_x_text(mkpost()))
        finally:
            os.environ.pop("SYNDICATE_DISCLOSE_AI", None) if old is None else os.environ.__setitem__("SYNDICATE_DISCLOSE_AI", old)

    def test_no_ai_note_for_a_post_not_marked_ai_assisted(self):
        p = mkpost(ai=False)
        self.assertNotIn("AI assistance", s.compose_linkedin(p)["commentary"])
        self.assertNotIn("AI assistance", s.compose_bluesky_text(p))
        self.assertNotIn("AI assistance", s.compose_x_text(p))

    def test_bluesky_text_within_limit_and_keeps_the_note(self):
        p = mkpost(excerpt="word " * 200)
        t = s.compose_bluesky_text(p)
        self.assertLessEqual(len(t), s.BLUESKY_TEXT_MAX)
        self.assertTrue(t.endswith("Drafted with AI assistance."))

    def test_bluesky_record_has_an_external_card_and_a_valid_timestamp(self):
        rec = s.compose_bluesky_record(mkpost(), now=dt.datetime(2026, 10, 6, 1, 2, 3, 456000, tzinfo=dt.timezone.utc))
        self.assertEqual(rec["$type"], "app.bsky.feed.post")
        self.assertEqual(rec["createdAt"], "2026-10-06T01:02:03.456Z")
        self.assertEqual(rec["embed"]["$type"], "app.bsky.embed.external")
        self.assertEqual(rec["embed"]["external"]["uri"], mkpost().url)

    def test_x_text_fits_with_the_url_counted_as_23(self):
        for ex in ("short", "word " * 300, "日本語 " * 120):
            p = mkpost(excerpt=ex, title="T " * 60)
            t = s.compose_x_text(p)
            self.assertLessEqual(s.x_text_weight(t, p.url), s.X_TEXT_MAX, ex[:10])
            self.assertTrue(t.endswith(p.url))

    def test_per_platform_overrides_win(self):
        p = mkpost("social:\n  linkedin: 'Custom (LI)'\n  bluesky: 'Custom BS'\n  twitter: 'Custom X'\n")
        self.assertEqual(s.compose_linkedin(p)["commentary"], "Custom \\(LI\\)")
        self.assertEqual(s.compose_bluesky_text(p), "Custom BS")
        self.assertEqual(s.compose_x_text(p), f"Custom X\n{p.url}")


class LinkedInTests(unittest.TestCase):
    ENV = {"LINKEDIN_ACCESS_TOKEN": "TOKEN-SECRET-123", "LINKEDIN_PERSON_URN": "urn:li:person:abc"}

    def test_success_returns_the_post_id_and_sends_the_required_headers(self):
        http = FakeHttp(Resp(201, headers={"x-restli-id": "urn:li:share:99"}))
        ident = s.post_linkedin(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(ident, "urn:li:share:99")
        method, url, kw = http.calls[0]
        self.assertEqual(url, "https://api.linkedin.com/rest/posts")
        h = kw["headers"]
        self.assertEqual(h["Authorization"], "Bearer TOKEN-SECRET-123")
        self.assertEqual(h["X-Restli-Protocol-Version"], "2.0.0")
        self.assertEqual(h["Linkedin-Version"], s.LINKEDIN_VERSION_DEFAULT)
        self.assertEqual(kw["json"]["author"], "urn:li:person:abc")

    def test_version_is_overridable(self):
        http = FakeHttp(Resp(201))
        s.post_linkedin(mkpost(), {**self.ENV, "LINKEDIN_VERSION": "203001"}, http, sleep=NOSLEEP)
        self.assertEqual(http.calls[0][2]["headers"]["Linkedin-Version"], "203001")

    def test_401_is_terminal_one_request_no_retry_and_no_token_in_the_message(self):
        http = FakeHttp(Resp(401, text="token TOKEN-SECRET-123 invalid"))
        with self.assertRaises(s.PostError) as cm:
            s.post_linkedin(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(len(http.calls), 1)
        self.assertNotIn("TOKEN-SECRET-123", str(cm.exception))
        self.assertIn("linkedin_auth.py", str(cm.exception))

    def test_a_secret_echoed_in_an_error_body_is_redacted(self):
        http = FakeHttp(Resp(422, text="bad body, token TOKEN-SECRET-123 was seen"))
        with self.assertRaises(s.PostError) as cm:
            s.post_linkedin(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertNotIn("TOKEN-SECRET-123", str(cm.exception))

    def test_a_5xx_is_not_retried_because_the_post_may_exist(self):
        http = FakeHttp(Resp(500), Resp(201))
        with self.assertRaises(s.PostError):
            s.post_linkedin(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(len(http.calls), 1)

    def test_a_429_honours_retry_after_then_succeeds(self):
        waits = []
        http = FakeHttp(Resp(429, headers={"Retry-After": "7"}), Resp(201, headers={"x-restli-id": "id1"}))
        ident = s.post_linkedin(mkpost(), self.ENV, http, sleep=waits.append)
        self.assertEqual(ident, "id1")
        self.assertEqual(len(http.calls), 2)
        self.assertEqual(waits, [7])

    def test_429_gives_up_after_the_retry_budget(self):
        http = FakeHttp(*[Resp(429)] * 5)
        with self.assertRaises(s.PostError):
            s.post_linkedin(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(len(http.calls), 3)

    def test_connection_error_is_retried_but_a_timeout_after_sending_is_not(self):
        http = FakeHttp(requests.exceptions.ConnectionError("x"), Resp(201))
        s.post_linkedin(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(len(http.calls), 2)
        http2 = FakeHttp(requests.exceptions.ReadTimeout("slow"), Resp(201))
        with self.assertRaises(s.PostError):
            s.post_linkedin(mkpost(), self.ENV, http2, sleep=NOSLEEP)
        self.assertEqual(len(http2.calls), 1)

    def test_a_retired_api_version_gets_an_actionable_message(self):
        with self.assertRaises(s.PostError) as cm:
            s.post_linkedin(mkpost(), self.ENV, FakeHttp(Resp(426)), sleep=NOSLEEP)
        self.assertIn("LINKEDIN_VERSION", str(cm.exception))


class BlueskyTests(unittest.TestCase):
    ENV = {"BLUESKY_HANDLE": "dlockamy.com", "BLUESKY_APP_PASSWORD": "app-pass-SECRET"}

    def test_logs_in_then_creates_the_record_on_the_right_repo(self):
        http = FakeHttp(Resp(200, {"accessJwt": "JWT", "did": "did:plc:abc"}), Resp(200, {"uri": "at://did:plc:abc/app.bsky.feed.post/1"}))
        ident = s.post_bluesky(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(ident, "at://did:plc:abc/app.bsky.feed.post/1")
        (_, u1, k1), (_, u2, k2) = http.calls
        self.assertTrue(u1.endswith("/xrpc/com.atproto.server.createSession"))
        self.assertEqual(k1["json"], {"identifier": "dlockamy.com", "password": "app-pass-SECRET"})
        self.assertTrue(u2.endswith("/xrpc/com.atproto.repo.createRecord"))
        self.assertEqual(k2["headers"]["Authorization"], "Bearer JWT")
        self.assertEqual(k2["json"]["repo"], "did:plc:abc")
        self.assertEqual(k2["json"]["collection"], "app.bsky.feed.post")

    def test_a_failed_login_stops_before_posting_and_hides_the_password(self):
        http = FakeHttp(Resp(401, text="bad password app-pass-SECRET"))
        with self.assertRaises(s.PostError) as cm:
            s.post_bluesky(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(len(http.calls), 1)
        self.assertNotIn("app-pass-SECRET", str(cm.exception).replace("app password", ""))


class XTests(unittest.TestCase):
    ENV = {"X_API_KEY": "k", "X_API_SECRET": "ks", "X_ACCESS_TOKEN": "t", "X_ACCESS_SECRET": "ts"}

    def test_posts_with_oauth1_user_auth(self):
        from requests_oauthlib import OAuth1

        http = FakeHttp(Resp(201, {"data": {"id": "123"}}))
        self.assertEqual(s.post_x(mkpost(), self.ENV, http, sleep=NOSLEEP), "123")
        _, url, kw = http.calls[0]
        self.assertEqual(url, "https://api.x.com/2/tweets")
        self.assertIsInstance(kw["auth"], OAuth1)
        self.assertIn(mkpost().url, kw["json"]["text"])

    def test_no_credits_gets_a_clear_message_and_is_not_retried(self):
        http = FakeHttp(Resp(402), Resp(201))
        with self.assertRaises(s.PostError) as cm:
            s.post_x(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertIn("credits", str(cm.exception))
        self.assertEqual(len(http.calls), 1)


class CommandTests(unittest.TestCase):
    def _run_post(self, platform, env, http, **kw):
        a = Namespace(post=kw.get("post", "x.md"), platform=platform, dry_run=kw.get("dry_run", False), wait_live=kw.get("wait_live", 0))
        old = s.parse_post
        s.parse_post = lambda path, text=None: mkpost()
        try:
            return s.cmd_post(a, env=env, http=http, sleep=NOSLEEP)
        finally:
            s.parse_post = old

    def test_missing_credentials_skip_cleanly_with_no_http_at_all(self):
        http = FakeHttp()
        self.assertEqual(self._run_post("linkedin", {}, http), 0)
        self.assertEqual(http.calls, [])

    def test_dry_run_never_touches_the_network_even_with_credentials(self):
        http = FakeHttp()
        env = {"LINKEDIN_ACCESS_TOKEN": "t", "LINKEDIN_PERSON_URN": "u"}
        self.assertEqual(self._run_post("linkedin", env, http, dry_run=True), 0)
        self.assertEqual(http.calls, [])

    def test_failure_returns_nonzero_so_the_job_is_red_and_rerunnable(self):
        env = {"LINKEDIN_ACCESS_TOKEN": "t", "LINKEDIN_PERSON_URN": "u"}
        self.assertEqual(self._run_post("linkedin", env, FakeHttp(Resp(401))), 1)

    def test_nothing_is_posted_if_the_post_never_goes_live(self):
        http = FakeHttp(default=Resp(404))
        env = {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}
        ticks = iter(range(0, 10_000, 50))
        a = Namespace(post="x.md", platform="bluesky", dry_run=False, wait_live=100)
        old = s.parse_post
        s.parse_post = lambda path, text=None: mkpost()
        try:
            rc = s.cmd_post(a, env=env, http=http, sleep=NOSLEEP, clock=lambda: next(ticks))
        finally:
            s.parse_post = old
        self.assertEqual(rc, 1)
        self.assertTrue(http.calls and all(c[0] == "get" for c in http.calls), "must not have posted anything")

    def test_wait_live_succeeds_once_the_page_appears(self):
        http = FakeHttp(Resp(404), Resp(404), Resp(200))
        t = iter(range(0, 1000, 5))
        self.assertTrue(s.wait_live("http://x", http, timeout=900, interval=20, sleep=NOSLEEP, clock=lambda: next(t)))
        self.assertEqual(len(http.calls), 3)


class DetectTests(unittest.TestCase):
    def _git(self, cwd, *args):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})

    def _head(self, cwd):
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True).stdout.strip()

    def _write(self, d, name, extra=""):
        (Path(d) / "_posts").mkdir(exist_ok=True)
        (Path(d) / "_posts" / name).write_text(f'---\ntitle: "T {name}"\ndate: {name[:10]}\nexcerpt: "e"\n{extra}---\nbody\n')

    def test_only_added_and_opted_in_posts_are_selected(self):
        with tempfile.TemporaryDirectory() as d:
            self._git(d, "init", "-q")
            self._write(d, "2026-01-01-old.md", "syndicate: true\n")
            self._git(d, "add", "."); self._git(d, "commit", "-qm", "base")
            base = self._head(d)
            self._write(d, "2026-01-01-old.md", "syndicate: true\nedited: yes\n")      # edited, not added
            self._write(d, "2026-02-01-new-yes.md", "syndicate: [linkedin, bluesky]\n")  # added + opted in
            self._write(d, "2026-02-02-new-no.md")                                       # added, not opted in
            (Path(d) / "README.md").write_text("x")
            self._git(d, "add", "."); self._git(d, "commit", "-qm", "push")
            added = s.added_posts(base, self._head(d), repo=d)
            self.assertEqual(added, ["_posts/2026-02-01-new-yes.md", "_posts/2026-02-02-new-no.md"])
            m = s.build_matrix(added, repo=d)
            self.assertEqual(sorted((i["post"], i["platform"]) for i in m["include"]),
                             [("_posts/2026-02-01-new-yes.md", "bluesky"), ("_posts/2026-02-01-new-yes.md", "linkedin")])

    def test_first_push_of_a_branch_has_an_all_zero_before(self):
        with tempfile.TemporaryDirectory() as d:
            self._git(d, "init", "-q")
            self._write(d, "2026-03-01-first.md", "syndicate: true\n")
            self._git(d, "add", "."); self._git(d, "commit", "-qm", "first")
            self.assertEqual(s.added_posts("0" * 40, self._head(d), repo=d), ["_posts/2026-03-01-first.md"])

    def test_manual_run_can_force_a_post_that_is_not_opted_in(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "2026-04-01-m.md")
            m = s.build_matrix(["_posts/2026-04-01-m.md"], repo=d, platforms={"bluesky"}, force=True)
            self.assertEqual([i["platform"] for i in m["include"]], ["bluesky"])


class TokenCheckTests(unittest.TestCase):
    LI = {"LINKEDIN_ACCESS_TOKEN": "t", "LINKEDIN_CLIENT_ID": "i", "LINKEDIN_CLIENT_SECRET": "c"}

    def _check(self, env, http, warn=14):
        return s.cmd_check_tokens(Namespace(warn_days=warn, report=None), env=env, http=http)

    def test_nothing_configured_is_fine(self):
        self.assertEqual(self._check({}, FakeHttp()), 0)

    def test_plenty_of_time_left(self):
        import time
        http = FakeHttp(Resp(200, {"active": True, "expires_at": int(time.time()) + 40 * 86400}))
        self.assertEqual(self._check(self.LI, http), 0)

    def test_close_to_expiry_needs_attention(self):
        import time
        http = FakeHttp(Resp(200, {"active": True, "expires_at": int(time.time()) + 5 * 86400}))
        self.assertEqual(self._check(self.LI, http), 2)

    def test_an_inactive_token_needs_attention(self):
        self.assertEqual(self._check(self.LI, FakeHttp(Resp(200, {"active": False}))), 2)

    def test_a_revoked_bluesky_password_needs_attention(self):
        env = {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}
        self.assertEqual(self._check(env, FakeHttp(Resp(401))), 2)


class MastodonTests(unittest.TestCase):
    ENV = {"MASTODON_INSTANCE": "hachyderm.io", "MASTODON_ACCESS_TOKEN": "MASTO-SECRET-TOKEN"}
    INSTANCE_OK = Resp(200, {"configuration": {"statuses": {"max_characters": 500, "characters_reserved_per_url": 23}}})

    def test_instance_normalisation(self):
        for raw in ("hachyderm.io", "https://hachyderm.io", "https://HACHYDERM.io/", "  hachyderm.io  "):
            self.assertEqual(s.mastodon_base(raw), "https://hachyderm.io")
        self.assertEqual(s.mastodon_base("https://social.example:8443"), "https://social.example:8443")

    def test_instance_rejects_anything_that_is_not_a_plain_https_host(self):
        for bad in ("", "http://hachyderm.io", "https://hachyderm.io/path", "https://user:pw@hachyderm.io",
                    "https://hachyderm.io?x=1", "localhost", "https://exa mple.com", "file:///etc/passwd"):
            with self.assertRaises(s.PostError, msg=bad):
                s.mastodon_base(bad)

    def test_text_fits_with_the_url_counted_as_23_whatever_its_length(self):
        for ex in ("short", "word " * 400, "日本語 " * 200):
            p = mkpost(excerpt=ex)
            t = s.compose_mastodon_text(p, 500, 23)
            self.assertLessEqual(s.mastodon_length(t, p.url, 23), 500, ex[:8])
            self.assertTrue(t.endswith(p.url))
        self.assertIn("Drafted with AI assistance.", s.compose_mastodon_text(mkpost(excerpt="word " * 400), 500, 23))

    def test_a_smaller_server_limit_is_respected(self):
        p = mkpost(excerpt="word " * 400)
        self.assertLessEqual(s.mastodon_length(s.compose_mastodon_text(p, 300, 23), p.url, 23), 300)

    def test_override_wins_and_gets_the_url(self):
        p = mkpost("social:\n  mastodon: 'My own words'\n")
        self.assertEqual(s.compose_mastodon_text(p), f"My own words\n\n{p.url}")

    def test_posts_with_the_right_request_and_returns_the_status_url(self):
        http = FakeHttp(self.INSTANCE_OK, Resp(200, {"id": "1", "url": "https://hachyderm.io/@dlockamy/1"}))
        ident = s.post_mastodon(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(ident, "https://hachyderm.io/@dlockamy/1")
        (_, u1, _), (_, u2, kw) = http.calls
        self.assertEqual(u1, "https://hachyderm.io/api/v2/instance")
        self.assertEqual(u2, "https://hachyderm.io/api/v1/statuses")
        self.assertEqual(kw["headers"]["Authorization"], "Bearer MASTO-SECRET-TOKEN")
        self.assertEqual(kw["json"]["visibility"], "public")
        self.assertEqual(kw["json"]["language"], "en")
        self.assertIn(mkpost().url, kw["json"]["status"])

    def test_the_idempotency_key_is_stable_per_post_and_differs_between_posts(self):
        def key(p):
            http = FakeHttp(self.INSTANCE_OK, Resp(200, {"id": "1"}))
            s.post_mastodon(p, self.ENV, http, sleep=NOSLEEP)
            return http.calls[1][2]["headers"]["Idempotency-Key"]
        a1, a2 = key(mkpost()), key(mkpost())
        b = key(mkpost(date="2026-10-06"))
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, b)

    def test_uses_the_servers_own_character_limit(self):
        small = Resp(200, {"configuration": {"statuses": {"max_characters": 300, "characters_reserved_per_url": 23}}})
        http = FakeHttp(small, Resp(200, {"id": "1"}))
        s.post_mastodon(mkpost(excerpt="word " * 400), self.ENV, http, sleep=NOSLEEP)
        sent = http.calls[1][2]["json"]["status"]
        self.assertLessEqual(s.mastodon_length(sent, mkpost().url, 23), 300)

    def test_falls_back_to_defaults_if_the_instance_endpoint_is_unreadable(self):
        http = FakeHttp(Resp(500), Resp(200, {"id": "1"}))
        s.post_mastodon(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertEqual(len(http.calls), 2)

    def test_visibility_is_validated_and_configurable(self):
        http = FakeHttp(self.INSTANCE_OK, Resp(200, {"id": "1"}))
        s.post_mastodon(mkpost(), {**self.ENV, "MASTODON_VISIBILITY": "unlisted"}, http, sleep=NOSLEEP)
        self.assertEqual(http.calls[1][2]["json"]["visibility"], "unlisted")
        with self.assertRaises(s.PostError):
            s.post_mastodon(mkpost(), {**self.ENV, "MASTODON_VISIBILITY": "everyone"}, FakeHttp(), sleep=NOSLEEP)

    def test_401_and_403_are_terminal_with_actionable_messages_and_no_token(self):
        for code, word in ((401, "invalid or revoked"), (403, "write:statuses")):
            http = FakeHttp(self.INSTANCE_OK, Resp(code, text="token MASTO-SECRET-TOKEN rejected"), Resp(200, {"id": "x"}))
            with self.assertRaises(s.PostError) as cm:
                s.post_mastodon(mkpost(), self.ENV, http, sleep=NOSLEEP)
            self.assertIn(word, str(cm.exception))
            self.assertNotIn("MASTO-SECRET-TOKEN", str(cm.exception))
            self.assertEqual(len(http.calls), 2, "the post must not be retried")

    def test_a_token_echoed_in_an_error_body_is_redacted(self):
        # statuses with no fixed hint print the response body, so this is where redaction matters
        http = FakeHttp(self.INSTANCE_OK, Resp(500, text="upstream error, saw token MASTO-SECRET-TOKEN"))
        with self.assertRaises(s.PostError) as cm:
            s.post_mastodon(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertIn("HTTP 500", str(cm.exception))
        self.assertNotIn("MASTO-SECRET-TOKEN", str(cm.exception))

    def test_a_422_explains_itself(self):
        http = FakeHttp(self.INSTANCE_OK, Resp(422, text="Validation failed"))
        with self.assertRaises(s.PostError) as cm:
            s.post_mastodon(mkpost(), self.ENV, http, sleep=NOSLEEP)
        self.assertIn("rejected", str(cm.exception))

    def test_skipped_cleanly_without_credentials(self):
        self.assertEqual(s.missing_credentials("mastodon", {}), ["MASTODON_INSTANCE", "MASTODON_ACCESS_TOKEN"])
        self.assertEqual(s.missing_credentials("mastodon", self.ENV), [])

    def test_token_check_ok_and_rejected(self):
        ok = Namespace(warn_days=14, report=None)
        self.assertEqual(s.cmd_check_tokens(ok, env=self.ENV, http=FakeHttp(Resp(200, {"name": "app"}))), 0)
        self.assertEqual(s.cmd_check_tokens(ok, env=self.ENV, http=FakeHttp(Resp(401))), 2)
        self.assertEqual(s.cmd_check_tokens(ok, env={**self.ENV, "MASTODON_INSTANCE": "http://bad"}, http=FakeHttp()), 2)


class LinkedInAuthTests(unittest.TestCase):
    """The browser round-trip itself cannot be tested offline; these cover the parts that can."""

    def setUp(self):
        import linkedin_auth
        self.la = linkedin_auth

    def test_auth_url_has_the_scopes_state_and_exact_redirect(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.la.build_auth_url("CID", 8765, "STATE1"))
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        self.assertEqual(u.netloc, "www.linkedin.com")
        self.assertEqual(q["response_type"], "code")
        self.assertEqual(q["client_id"], "CID")
        self.assertEqual(q["redirect_uri"], "http://localhost:8765/callback")
        self.assertEqual(q["state"], "STATE1")
        self.assertEqual(set(q["scope"].split()), {"openid", "profile", "w_member_social"})

    def test_secrets_go_to_gh_on_stdin_and_never_on_the_command_line(self):
        calls = []

        def fake_run(cmd, **kw):
            calls.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0, "", "")

        self.la.set_secret("LINKEDIN_ACCESS_TOKEN", "TOP-SECRET-TOKEN", "o/r", run=fake_run)
        cmd, kw = calls[0]
        self.assertEqual(cmd, ["gh", "secret", "set", "LINKEDIN_ACCESS_TOKEN", "--repo", "o/r"])
        self.assertNotIn("TOP-SECRET-TOKEN", " ".join(cmd))
        self.assertEqual(kw["input"], "TOP-SECRET-TOKEN")

    def test_token_exchange_and_member_urn(self):
        http = FakeHttp(Resp(200, {"access_token": "AT", "expires_in": 5183999, "scope": "openid,profile,w_member_social"}),
                        Resp(200, {"sub": "abc123", "name": "D L"}))
        tok = self.la.exchange_code(http, "CID", "CSEC", "CODE", 8765)
        self.assertEqual(tok["access_token"], "AT")
        self.assertEqual(http.calls[0][2]["data"]["grant_type"], "authorization_code")
        self.assertEqual(http.calls[0][2]["data"]["redirect_uri"], "http://localhost:8765/callback")
        self.assertEqual(self.la.member_urn(http, "AT"), "urn:li:person:abc123")
        self.assertEqual(http.calls[1][2]["headers"]["Authorization"], "Bearer AT")


    def test_the_localhost_callback_is_really_served_and_parsed(self):
        import socket
        import threading

        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        ready, out = threading.Event(), {}
        th = threading.Thread(target=lambda: out.update(self.la.wait_for_callback(port, timeout=10, ready=ready)))
        th.start()
        self.assertTrue(ready.wait(5))
        r = requests.get(f"http://127.0.0.1:{port}/callback?code=THE-CODE&state=THE-STATE", timeout=5)
        th.join(10)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(out, {"code": "THE-CODE", "state": "THE-STATE"})
        self.assertNotIn("THE-CODE", r.text)  # the page must not echo the code

    def test_callback_times_out_cleanly_when_nobody_answers(self):
        import socket
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        self.assertEqual(self.la.wait_for_callback(port, timeout=1), {})

    def test_a_failed_exchange_stops_with_a_message(self):
        with self.assertRaises(SystemExit):
            self.la.exchange_code(FakeHttp(Resp(400, text="invalid_client")), "CID", "CSEC", "CODE", 8765)


if __name__ == "__main__":
    unittest.main()
