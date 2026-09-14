---
layout: post
title: "Thirteen sketches, a permission that could launder itself, and a nav I haven't shipped yet"
date: 2026-09-13
categories: [quickring, architecture]
tags: [quickring, courier, flutter, dart, rust, flutter_rust_bridge, navigation, security, git]
excerpt: "This week I tore out Courier's shipping four-tab bottom bar and rebuilt the navigation from scratch — QR-226, a people-first launcher instead of another persistent bar. It took thirteen throwaway sketch rounds, a ten-agent design review that caught a smart-home permission that could quietly launder itself, and ten real commits on a feature branch. What I did not do is ship it. The branch is pushed, not merged; all six destinations run on mock data; and real-device testing is still ahead of me. Here's the whole arc, including the two environment blockers that had nothing to do with the nav and the handoff mistake I nearly made."
author: Douglas Lockamy
ai_assisted: true
---

Courier — Quickring's messaging app — has shipped with a four-tab bottom
bar for a while now: Messages, Media, House, Settings, landing you on
Messages. It works. It's also the most generic thing about the app, and
the longer I lived with it the more it bothered me for a reason I couldn't
immediately name. Eventually I could: the bar organizes the app around
*what the tech does* — here are your messages, here is your media, here is
your house — when the thing I actually want Courier to be organized around
is *the people you're keeping up with*. A persistent tab bar is a filing
cabinet. I wanted something closer to walking into a room and seeing who's
around.

So this week I rebuilt the navigation from scratch. Internally it's
QR-226, and it supersedes QR-180, the four-tab bar that's currently
shipping. I want to be precise about tense up front, because the rest of
this post earns it: I *built* a replacement. I have not *shipped* one. The
branch is pushed and unmerged, and I'll get to exactly what "unmerged"
means here before the end.

---

## Thirteen sketches before a line of real code

I didn't start in the real codebase. I started in a throwaway sketch
directory — `sketches/nav-experiment-people-first/` in the Courier repo —
and I went through thirteen iteration rounds in it. Not thirteen tweaks;
thirteen rounds, each one a real, buildable pass at the whole idea, each
one throwing out or keeping decisions from the last.

The discipline I held myself to is the part worth naming, because it's the
only reason I trust what came out the other end. Every round was
independently verified before I was allowed to start the next one:
`flutter analyze` clean, `flutter test` clean, and — this is the one people
skip — a live Chrome build that I actually clicked through. Not "it
compiled." Not "the widget tree looks right." I opened the thing and used
it, every round, thirteen times. When it stopped being annoying to use, I
stopped.

I kept the sketch directory committed rather than deleting it. It's not
production code and it never will be, but it's the reasoning trail for why
the final shape looks the way it does, and future-me is going to want that
more than a clean tree.

## What it landed on

The shipping bar is a *persistent* structure — it's always there, always
watching you from the bottom of the screen. What I landed on is
deliberately not that. It's a root-level launcher: a 2×3 icon grid,
hub-and-spoke, push-based. You start at the hub, you push into a
destination, you come back to the hub. No permanent bar following you
around. Six destinations:

- **Today** — a single blended attention view across every section,
  ordered by a mix of time and weight. The one screen that answers "what
  actually needs me right now" without making me check six places.
- **Catching Up** — named collections of updates from the people you're
  closest to. This one is deliberately non-algorithmic. It's modeled on
  the early-Facebook feeling of *checking in on people*, not on a feed
  engineered to keep you scrolling. There is nothing to optimize here on
  purpose.
- **People** — cross-protocol contact merging: SMS, email, and Quickring
  threads collapsed into one contact. Crucially, it's honest about the
  seams. A thread that's fully end-to-end shows as **Unified**; one that's
  relayed through a bridge shows as **Bridged**. I'm not going to paint
  over the difference between "this is private end to end" and "this passed
  through a relay" — the user gets to see which is which.
- **Desk** — channels, tracked work items, and file authoring. The
  get-things-done surface.
- **Den** — a cross-media "Up Next" queue for movies, TV, and games,
  modeled on the Apple TV app. The interesting constraint here is that the
  *source* of a given item is structurally invisible: there is no field in
  the code for which backend a title came from. You can't accidentally leak
  it because it doesn't exist to leak.
- **Files** — a cross-type store that, instead of asking you to pick a
  format up front, walks you through a two-round proxy-question wizard —
  it asks about what you're trying to do, not what extension you want.

Two things sit outside the grid on purpose. **Scenes** — smart-home
control — is its own category, not a room and not a lens over one of the
six; it didn't fit cleanly inside any destination without distorting it, so
it doesn't. And **Settings** is a persistent gear icon, deliberately *not*
promoted to a seventh tile. Settings is not a destination you're supposed
to want to visit.

## The review, and the catch

Before I touched a single line of real implementation code, I ran the
finished sketch through a ten-agent cross-discipline review: product,
security, data architecture, protocol, creative direction, brand, sound,
design systems, QA, and monetization. The point was to find the problems
while they were still cheap — while they lived in a sketch driven by mock
data and not in shipped code.

The standout catch came from the security reviewer, and it's a good
example of why you do this before you build and not after. In the sketch,
Scenes' actions — create a scene, trigger a scene, modify a scene — were
one undifferentiated permission grant. They *looked* like separate buttons,
but underneath they were the same capability. On a shared smart-home scene,
that means someone with mere "trigger" access could reach the "modify"
path, because the code never actually distinguished them. That's a
permission you could launder into a permission you don't have.

I want to be exact about the severity here, because it's easy to make this
sound scarier than it was: this was caught in design review, against mock
data, before any real implementation existed. Nothing shipped. No user was
ever exposed to it. It was a flaw in a drawing, found while it was still a
drawing — which is the entire reason the drawing existed. The fix carried
into the real implementation as an architectural rule rather than a visual
one: trigger, modify, and create are now genuinely separate call paths, not
three buttons wired to the same door.

## The go-ahead

After the review I made the call to build it for real. The exact wording I
gave myself was *"Yes, we should proceed on all accounts... Let's build
this out for real,"* and I'm quoting it because it's the honest pivot
point — the line between "interesting experiment in a sketch folder" and
"I'm now going to spend real commits on this and delete the thing that
currently ships."

---

## Building it for real

I wrote a real successor spec first, then landed ten real commits on a
feature branch, `feat/qr226-nav-v2-people-first`. Same discipline as the
sketches, higher stakes: each commit independently verified before the next
one started — `flutter analyze` clean, `flutter test` clean, and a real
`flutter build apk --debug` that produced an actual APK, not a promise of
one.

There was one test failure in the suite, and I want to account for it
rather than wave it off. It's pre-existing: I diffed against `origin/main`
and confirmed it already fails there, before any of my work started. It's
unrelated to the nav, and I didn't let its red distract me from the green
I actually owned — but I also didn't get to claim a clean suite I didn't
have.

The part I'm most deliberate about: I *deleted* the old QR-180 nav shell.
Its `StatefulShellRoute`, the shell scaffolding, the nav-rail plumbing —
all of it, gone, not left behind a feature flag. Dead code kept "just in
case" is a security blanket that costs you later; if the new thing is the
thing, the old thing should stop existing. If I need it back, that's what
git is for.

## Two blockers that had nothing to do with the nav

Some of the week went to problems that were pure environment tax and had
nothing to do with navigation at all. Logging them because next time I want
past-me to have written this down.

First: the checkout had never bootstrapped its Rust / `flutter_rust_bridge`
toolchain. Nothing compiled — not the nav, not anything — until I sorted
that out. The app leans on a Rust core through the bridge, and a fresh
checkout that's never generated that binding is just a pile of Dart calling
into nothing.

Second, and more annoying: the Android build failed with a Kotlin DSL
`unresolved reference` error that told me nothing true. The real cause was
that my local Flutter — 3.41.9, installed via Homebrew — was too old; the
project needs Flutter ≥ 3.44. The error had nothing to do with Kotlin and
everything to do with a version floor, which is the worst kind of error:
confidently pointing at the wrong thing. I fixed it without disturbing the
Homebrew install — downloaded Flutter 3.44.0 to a scratch location and
prefixed `PATH` with it for the session. No system-wide surgery to unblock
one build.

## The handoff I almost got backwards

Here's the mistake I nearly made, kept in because catching it is the whole
point. My plan was to push the branch *after* a second machine finished
testing it. I actually wrote that down as the order of operations before it
hit me that it's backwards: a second machine has nothing to fetch if the
branch was never pushed. The test can't precede the push; the push is what
makes the test possible.

So I pushed first — and then I didn't trust the push. `git push` printing
success is not the same as the commit being reachable from the remote, and
a handoff that assumes the two are identical is a handoff that fails
silently. I did a fresh fetch and ran `git merge-base --is-ancestor` to
confirm my final commit was genuinely an ancestor of the remote branch tip
before I called it handed off. The branch is really there. I checked,
rather than believing the output that told me it was.

---

## Where this actually stands

Now the part where I don't oversell it, because the temptation after a week
like this is to write "Courier has a new nav" and let you assume it's in
your hands. It isn't. Being exact:

- The branch is **pushed but not merged to main.** What ships today is
  still QR-180's four-tab bar.
- All six destinations currently run on **UI-only, in-memory mock data.**
  That's this codebase's established pattern — we build the screen ahead of
  its real backend and wire it up later — but I'm naming it plainly so it
  doesn't read as "done." The screens are real; the data behind them is
  not yet.
- `flutter analyze`, `flutter test`, and a debug APK build are real and
  complete — I can state those without an asterisk.
- **Real Android hardware testing has not happened.** That's the explicit
  next step, and it's now in a second machine's hands.

Also not built yet, so I'm not implying otherwise: Today's
scrub-to-navigate interaction; real per-device smart-home communication;
Scenes' *real* permission enforcement (that one's blocked on a separate
household-identity project that isn't finished — the architecture is
correct now, but the enforcement it depends on isn't there to lean on
yet); Scenes' sound feedback; and some longer-term data-model work.

The honest one-line summary: I replaced Courier's navigation in a feature
branch, from a thirteen-round sketch through a ten-agent review through ten
verified commits, and it is now waiting on real-device testing before it
can become anything you'd actually touch. The interesting work this week
wasn't the grid. It was catching a permission that could launder itself
while it was still a drawing, and catching a handoff I'd sequenced
backwards before it cost anyone a wasted fetch.

---

Unrelated, and purely a personal weekend thing with no connection to any
studio product: I also stood up a Minecraft Bedrock server on a home Linux
box this week, plain Docker, so I could play on LAN with a PS5. The only
part worth mentioning is that I didn't rediscover a bug I'd already solved —
a health-check/networking issue I'd diagnosed in a completely different
context applied cleanly here, so I reused the fix instead of re-earning it.
And I didn't trust the container reporting itself "healthy" as proof it
worked; I confirmed it with a raw network ping test over the LAN first.
Same reflex as the rest of the week, smaller stakes: the tool telling you
it's fine is a claim, not a verification.
