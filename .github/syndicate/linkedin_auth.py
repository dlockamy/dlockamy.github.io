#!/usr/bin/env python3
"""One-time (then every ~60 days) LinkedIn authorization for the blog's cross-poster.

Run this on your own machine, in a terminal, after creating the LinkedIn app
(see .github/SYNDICATION.md):

    python3 .github/syndicate/linkedin_auth.py --client-id YOUR_CLIENT_ID

It opens LinkedIn's consent page, catches the redirect on localhost, exchanges the
code for an access token, looks up your member id, and stores these as GitHub
Actions secrets on the repo using the `gh` CLI (the token goes straight from this
process into `gh`'s stdin: it is never printed, never written to disk, never on a
command line):

    LINKEDIN_ACCESS_TOKEN   LINKEDIN_PERSON_URN
    LINKEDIN_CLIENT_ID      LINKEDIN_CLIENT_SECRET   (the last two let the weekly
                                                       check read the token's expiry)

LinkedIn does not issue refresh tokens to self-serve apps, so the token lasts 60 days
and this script has to be run again. The weekly workflow opens an issue before then.
"""
from __future__ import annotations

import argparse
import getpass
import http.server
import os
import secrets as pysecrets
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPES = "openid profile w_member_social"
DEFAULT_PORT = 8765
DEFAULT_REPO = "dlockamy/dlockamy.github.io"


def redirect_uri(port: int) -> str:
    return f"http://localhost:{port}/callback"


def build_auth_url(client_id: str, port: int, state: str) -> str:
    q = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri(port),
        "state": state,
        "scope": SCOPES,
    })
    return f"{AUTH_URL}?{q}"


class _Handler(http.server.BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        if u.path != "/callback":
            self.send_response(404); self.end_headers(); return
        _Handler.result = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"LinkedIn authorization received. You can close this tab and go back to the terminal.\n")

    def log_message(self, *a):  # keep the code and state out of the terminal
        pass


def wait_for_callback(port: int, timeout: int = 300, ready: "threading.Event | None" = None) -> dict:
    """Serve one localhost redirect and return its query parameters ({} on timeout)."""
    _Handler.result = {}
    srv = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    srv.timeout = 1
    if ready is not None:
        ready.set()
    deadline = time.time() + timeout
    try:
        while time.time() < deadline and not _Handler.result:
            srv.handle_request()
    finally:
        srv.server_close()
    return _Handler.result


def exchange_code(http, client_id: str, client_secret: str, code: str, port: int) -> dict:
    r = http.post(TOKEN_URL, data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(port),
        "client_id": client_id, "client_secret": client_secret,
    }, timeout=30)
    if r.status_code != 200:
        # LinkedIn's error body names the problem (bad secret, redirect mismatch); it does not echo our secret.
        raise SystemExit(f"LinkedIn token exchange failed (HTTP {r.status_code}): {r.text[:300]}")
    return r.json()


def member_urn(http, access_token: str) -> str:
    r = http.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    if r.status_code != 200:
        raise SystemExit(
            f"Could not read your LinkedIn member id (HTTP {r.status_code}). Does the app have the "
            "'Sign In with LinkedIn using OpenID Connect' product? {r.text[:200]}"
        )
    return f"urn:li:person:{r.json()['sub']}"


def set_secret(name: str, value: str, repo: str, run=subprocess.run) -> None:
    """Value goes to gh on stdin, never argv (argv is visible in `ps`)."""
    p = run(["gh", "secret", "set", name, "--repo", repo], input=value, text=True, capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f"gh secret set {name} failed: {p.stderr.strip()[:200]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true", help="print the URL instead of opening it")
    a = ap.parse_args(argv)

    import requests

    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET") or getpass.getpass("LinkedIn app Client Secret (hidden): ")
    if not client_secret:
        raise SystemExit("a client secret is required")
    state = pysecrets.token_urlsafe(24)
    url = build_auth_url(a.client_id, a.port, state)
    print(f"Make sure {redirect_uri(a.port)} is listed under 'Authorized redirect URLs' in the app's Auth tab.")
    print("Opening LinkedIn. If nothing opens, paste this URL into a browser:\n" + url + "\n")
    if not a.no_browser:
        webbrowser.open(url)
    res = wait_for_callback(a.port)
    if not res:
        raise SystemExit("Timed out waiting for LinkedIn (5 minutes).")
    if res.get("error"):
        raise SystemExit(f"LinkedIn returned an error: {res.get('error')}: {res.get('error_description', '')}")
    if res.get("state") != state:
        raise SystemExit("State mismatch: the redirect did not come from the request this script made. Nothing was stored.")
    tok = exchange_code(requests, a.client_id, client_secret, res["code"], a.port)
    access, expires_in = tok["access_token"], int(tok.get("expires_in", 0))
    urn = member_urn(requests, access)

    for name, value in (("LINKEDIN_ACCESS_TOKEN", access), ("LINKEDIN_PERSON_URN", urn),
                        ("LINKEDIN_CLIENT_ID", a.client_id), ("LINKEDIN_CLIENT_SECRET", client_secret)):
        set_secret(name, value, a.repo)
        print(f"  stored {name} on {a.repo}")
    expiry = time.strftime("%Y-%m-%d", time.localtime(time.time() + expires_in))
    print(f"\nDone. The token expires about {expiry}. Granted scope: {tok.get('scope', '?')}")
    print("Check it any time with: gh workflow run 'Syndication token check' --repo " + a.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
