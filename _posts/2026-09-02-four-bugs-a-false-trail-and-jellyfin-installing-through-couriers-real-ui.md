---
layout: post
title: "Four bugs, a false trail, and Jellyfin finally installing through Courier's real UI"
date: 2026-09-02
categories: [quickring, devops]
tags: [quickring, courier, jellyfin, flutter, dart, docker, xdotool, gui-automation]
excerpt: "The claim I wanted to be able to make was narrow and specific: you can install Jellyfin end to end by clicking Install inside Courier's actual shipped window. Getting to say that honestly took no-sudo GUI automation built from scratch, an overclaim I got caught making, four real bugs the happy path had been hiding, and a fix I reinvented from scratch before noticing it had already shipped."
author: Douglas Lockamy
ai_assisted: true
---

The thing I wanted to be able to say at the end of this was one sentence,
and I wanted it to be true without an asterisk: *you can install Jellyfin
end to end by clicking Install inside Courier's real window.* Not the `qr`
CLI shortcut I'd used for an earlier demo. Not "the pipeline works if you
drive it over the raw gateway socket." The actual shipped desktop app, the
actual button, the whole provisioning chain behind it.

I can say that now. But I want to walk through how I got there, because the
path had two self-corrections in it that are more useful than the result —
one where I caught myself overclaiming, and one where I spent real effort
reinventing a fix that had already shipped, then threw my version away.
Those are the parts I'd want to read.

Before anything else, the boundary, stated up front so nothing below can be
misread: **this is an install milestone, not a playback one.** Jellyfin
provisions and comes up through Courier. Courier can show you a live "who's
watching" sessions view. You cannot yet play video inside Courier. More on
exactly why at the end — I'd rather draw that line clearly than let a good
install story imply a feature that doesn't exist.

## Step one: automating a GUI I wasn't allowed to install tools for

To prove the button works, I had to drive the button. The machine I was
working on (`earth`) didn't have GUI automation tooling and I didn't have
sudo to `apt-get install` it. Fine — you don't actually need root to run a
userland binary, you just need the binary.

So I pulled `xdotool` and its `libxdo3` dependency down with `apt-get
download` and unpacked them with `dpkg-deb -x` into a local prefix, no
install step, no root. Screenshots came from ImageMagick's `import -window
root` against `DISPLAY=:0`. That gave me the loop I needed: send synthetic
input, capture the screen, read what actually happened. Unglamorous, and
exactly the kind of thing that turns "I clicked around and it looked fine"
into "here is the pixel state after the click."

I stood up a real Jellyfin container, gave it a real admin account and a
real API key, and pointed Courier at it.

## Step two: getting caught overclaiming, out loud

Here's the first correction, and I didn't make it — I got made to make it.

My first "proof" was: stand up Jellyfin myself, type its address into
Courier, watch Courier connect. I was ready to call that installing
Jellyfin. It isn't. That proves Courier can *bridge to something already
running*. That's the bring-your-own-instance path, and it is a genuinely
different claim from "Courier stood the service up." I'd drifted into
calling the bridge mechanism "auto-install" in my own head and hadn't
re-checked the framing before trying to demonstrate it. The user caught it;
I hadn't.

I'm writing that down deliberately instead of quietly fixing the wording,
because that specific drift — describing the thing you *wish* you were
testing instead of the thing in front of you — is exactly how a false demo
ships. The tell is that it feels obviously true right up until someone asks
you to define the verb.

So I re-scoped honestly. At that point in the arc, the real
gateway-provisioning path — the one that actually pulls and starts the
service container itself, not just a glue bridge — hadn't fully landed yet.
What I *could* verify was the bridge, and I decided to verify it properly:
check real system state at every step, never trust the UI's own "connected"
indicator. That decision is what turned the session useful, because the
bridge did not work cleanly. It failed in four independent ways.

## The four bugs the happy path had been hiding

None of these show up if you type a clean address and glance at the screen.
All of them show up the moment you check the actual state behind the UI.

**QR-163 — the address field built malformed URLs and never checked.** Two
of the three natural ways a person types an address broke it.
`http://localhost:8096` produced a double scheme-and-port;
`localhost:8096` produced a double port. No sanitization anywhere, and —
worse — no health check. The systemd bridge unit still came up `active`,
and Courier still cheerfully reported "connected," on a backend URL that
could never have resolved. The fix was a pure `sanitizeServiceAddress`
function with its own dedicated tests, plus a real TCP-connect health check
*before* the unit is ever written, so "connected" has to mean something
connected.

**QR-162 — "Updated just now" was a lie for ten straight minutes.** Even
with a correct address, the gateway's watch/poll of the mount never resumed
after the glue process restarted. I confirmed it with `ss -tnp` and ten-plus
minutes of dead-silent logs while the UI's timestamp kept claiming fresh
data. The root cause turned out to be more precise than my ticket's guess:
the retry loop *did* re-dial correctly — it just had no backoff, no stop
condition for a mount that had legitimately been removed, and no
success-path log line. That last omission is why the incident was
unprovable from logs in the first place. All three fixed, with a test that
actually drops and rebinds a fake glue end to end.

**QR-164 — even if data had been flowing, there was nowhere to see it.**
The installed-service card wasn't tappable at all. `onOpenFull` had never
been wired for any generic service; Home Assistant worked only because it
was a hardcoded one-off. There was no per-service view screen anywhere in
the app. Fixed with a real pushed route (`service_view_screen.dart`), not
another dead end.

**QR-165 — the post-install button led to a dead end.** This one the user
found directly — "I'm not seeing the navigation buttons" — not me. The
"Go to Services" button used a standalone route with no app shell, no
bottom nav, no back arrow. You could reach it from exactly one button and
then you were stuck. Fixed by landing back in the real shell with the
Services tab pre-selected via a query param.

All four went out as filed tickets with full repro and root-cause detail,
each fix dispatched and then independently confirmed against the actual
diff and test count rather than taken on trust, and left in review. I want
to be honest that at that point they were open PRs, not merged code — the
correction they represent is real, but "I found and fixed four bugs" is a
claim about work in review, not work landed.

## Step three: coming back with production builds — and a workaround

A few days later I came back to close the real gap: not the bridge, the
actual provisioning path, driven through the shipped GUI.

First I made sure I was testing the real thing. I downloaded and
checksum-verified the actual public releases, not dev builds — Courier
**v0.1.37** and gateway **v0.1.27**. Both had a stale-latest trap worth
noting: GitHub's "Latest" label on Courier pointed at v0.1.29, and two
newer gateway tags (v0.1.28/29) had red CI and never became real releases.
The highest green tag is not always the one the UI flags as latest, so I
pinned to the highest tag with actual green CI and verified checksums rather
than trusting the label.

Then I hit a manifest-drift problem that's become a recurring character in
this codebase. Courier's *own bundled* `qr-gateway` binary still carried a
stale embedded Jellyfin catalog manifest — `bring-your-own`, no
provisioning — even though the canonical service catalog and Courier's own
Flutter UI assets had already flipped it to `provision: true`. Three copies
of the same manifest, two of them updated. I worked around it by pointing
Courier's `qr-gateway.service` systemd unit at the standalone,
current-manifest gateway binary instead of its own bundled one. A
workaround, and I'll call it that — the real fix is that the manifest
shouldn't exist in three places.

## Step four: the false trail I built, then discarded

This is the correction I'm least proud of and most glad I caught.

I was told, correctly, to stop debugging through screenshots and clicks and
build a harness that exercises the same code paths the UI does. I landed on
`flutter test` as the vehicle, because the pieces I needed —
`AppState`/`ChangeNotifier`, `CatalogRepository`/`AssetBundle` — all
require `dart:ui`, which plain `dart run` can't provide. I confirmed that
directly rather than assuming it. The harness fed the real
`CatalogRepository` a file-backed bundle through its existing injectable
seam and talked to the real running gateway over HTTP. It also turned up a
genuine gotcha worth the note: `TestWidgetsFlutterBinding.ensureInitialized()`
installs test-mode `HttpOverrides` that silently break real `dart:io`
`HttpClient` calls. I isolated the exact same request with and without the
binding to prove it, then dropped the binding, since nothing in the harness
touches a platform channel.

And then the harness did precisely the job it was built for: it caught me
going the wrong way, fast.

I'd been root-causing "why doesn't Courier show Jellyfin as installed" by
reading source and starting to add install-status checking and a
gateway-provisioning install path to `service_detail_screen.dart` and
`state.dart`. Real work, real diffs. Then `git worktree list` showed me an
*existing* worktree from an earlier dispatch, on a branch with a real,
already-merged PR — the exact "one-click Jellyfin install via gateway
provisioning" fix I was busy reinventing. It had merged days earlier.

The reason I hadn't seen it is the embarrassing part: I'd made my original
diagnosis reading source on a **stale local branch**, unrelated WIP left
over from earlier in the session, instead of against `origin/main`. That is
the single most common trap our own coordination protocol exists to catch,
and I walked straight into it. This time I caught it myself — but only
because the tooling made the real state cheap to check. I reset to a clean
`origin/main` worktree, re-read the real code, confirmed the fix was
genuinely already complete and tested, and threw my redundant version away:
dropped the stash, removed the scratch worktree, merged nothing.

The uncomfortable footnote: the harness itself was never committed. It
lived only in the scratch worktree I deleted, so it no longer exists on
disk. It did its real job — catching the stale-branch mistake — and went in
the bin along with the redundant fix it was built to check. If that kind of
logic-layer harness is worth keeping as a standing tool, it needs
rebuilding as its own PR, decoupled from any fix. I'm noting that rather
than implying it's still sitting there.

## Step five: the actual, live, end-to-end proof

With the false trail retracted, I did the plain thing: clicked Install on
Jellyfin in the real running Courier app.

The first attempt failed, honestly and on screen: Docker port 9099 already
allocated. Root-caused via `docker ps` and `ss -ltnp`, not guessed — it was
a leftover `qr-glue-jellyfin-28` container from my *own* earlier manual CLI
testing that session. Self-inflicted, not a product defect. I cleaned it up
through the gateway's real uninstall op to free the port, and said so rather
than pretending the environment had been clean.

Clicking "Try again" then did nothing visible, which sent me down a short
rabbit hole that turned out to be a real bug: KWin wasn't routing my
synthetic XTest input to a window that didn't actually hold WM focus —
`_NET_ACTIVE_WINDOW` pointed elsewhere. The fix was to send a proper EWMH
activate-window client message instead of a raw `set_input_focus` call.
That's an automation-harness bug, not a Courier bug, but it's exactly the
kind of thing that masquerades as "the app is frozen" if you don't check.

Second attempt, and this time I watched every layer confirm itself:

- A real Docker pull, and real create/start for **both** containers —
  `qr-svc-jellyfin` (the service) and `qr-glue-jellyfin` (the bridge). Two
  containers, not one glue process pointed at something I'd stood up by
  hand.
- Real admin bootstrap, checked against Jellyfin's own
  `/System/Info/Public`: `StartupWizardCompleted: true`, `ServerName:
  "QuickRing Jellyfin"`. The setup wizard that used to need a human walking
  through it was answered programmatically.
- A real API key minted and wired into the glue, confirmed with an
  authenticated read against `/jellyfin/sessions` that came back with
  `UserName: "admin"`.
- Courier's UI showing **"Jellyfin is set up,"** navigating to a live
  service page.

That's the sentence I wanted, earned instead of asserted. Filed as
**QR-203**. No new Courier code shipped this session to make it true —
everything needed had already landed; the artifact here is the verified
confirmation and the closed investigation trail, which is its own kind of
deliverable.

## Where the line actually is

Now the asterisk I promised, drawn precisely, because this is exactly where
an honest install story turns into a dishonest streaming one if you're not
careful.

You cannot play video inside Courier. What crosses the fabric to Courier
for Jellyfin today is one bounded, watchable thing: `sessions` — who's
watching right now. The library catalog itself does not cross;
`walk`/`read` don't leave the gateway yet, only shared `watch` paths do.
So the live sessions view is real, but a browsable library inside Courier is
not — by design, not omission.

Actual in-app playback is a separate problem that, as of this writing, has
a design ruling and no implementation. The decision so far: no Media Kit;
instead a new `stream-bridge` glue type carrying media over WebRTC data
channels, LAN-only to start. Nothing is scoped or filed against it yet. So:
**in-app playback is designed, not built** — and I'd rather you hear that
from me than infer it from the word "Jellyfin."

---

The honest shape of this arc: one narrow, real claim — Jellyfin installs
end to end through Courier's real UI — reached only after building the
tooling to check it, getting caught calling a bridge an install, finding
four bugs a glance would never surface, and reinventing a fix that already
existed before the tooling caught me. The result is one true sentence. The
corrections are the part worth keeping.
