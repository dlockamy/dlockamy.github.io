---
layout: post
title: "A lightbulb over the fabric, and the Redis sidecar that almost took it back"
date: 2026-08-09
categories: [quickring, devops]
tags: [quickring, rust, flutter, jenkins, terraform, redis, infrastructure, home-assistant]
excerpt: "Verifying that a phone app can show you a real lightbulb's real state, over Quickring's fabric, should have been the easy part. It turned into a hub restart, three infrastructure bugs, and a Redis sidecar that quietly erased the morning's identity work while nobody was looking."
author: Douglas Lockamy
ai_assisted: true
---

The task, going into this weekend's last stretch, was small on paper:
confirm that Courier — the consumer app — can show you the real state of a
real Home Assistant light, delivered over Quickring's production fabric by
the household-OS gateway I'd been building all week. Tap a tile, watch a
real bulb change. That's it. That's the whole household-computing thesis in
one screenshot.

It took a hub restart, three separate infrastructure bugs, a from-scratch
Home Assistant rebuild, and a security call I didn't make alone before I
got that screenshot. Then, right after I got it, the thing that made it
possible quietly broke itself.

## The restart that wasn't supposed to be interesting

Courier couldn't authenticate onto the household account. Not a bug in
Courier — the production hub simply hadn't restarted since I'd staged its
new access token earlier in the day, and a hub restart was the one thing
I'd deliberately deferred that morning to avoid touching a live relay
mid-migration. Fine. Time to stop deferring it.

Except the deploy doc I went to follow described a hub that didn't exist
anymore. It said SSH onto a shared box and `docker compose up`. The hub had
actually moved onto its own ECS service on our shared platform ten days
earlier, and nobody had gone back and fixed the doc. Following it would
have "succeeded" against a machine the running hub had already left.

Once I was looking at the real deploy path, `terraform plan` itself
wouldn't even run — the CI identity was missing a permission to read a
secret it needed to resolve, a leftover from before that secret existed.
Easy fix, except fixing an IAM policy *by running Terraform as the identity
that policy governs* is exactly the kind of chicken-and-egg you'd expect,
and I ended up bootstrapping the grant out-of-band, once, to get past it.

Then the actual deploy hit a wall I wasn't going to just power through:
registering the new task definition needed permission to hand off to the
platform's shared execution role — and that role, I confirmed live, could
already read *both* our secrets and the neighboring product's secrets on
the same cluster. Widening our access into that role would have meant our
deploy pipeline could, incidentally, read someone else's production
credentials. That's not a judgment call to make solo at midnight. I got a
second opinion, the answer was "give the hub its own execution role," and
that's what shipped — scoped to exactly the two secrets it actually needs,
nothing borrowed.

Along the way, a failed attempt at the old approach briefly left the
running service pointed at a task definition that had just been
deregistered — stable, but one crash away from not being able to restart
itself. I closed that window immediately with a same-content replacement
while the real fix was still in progress, then made sure the actual fix
included `create_before_destroy`, so a future failed deploy leaves the old
version standing instead of stranding the service between two.

None of that was what I sat down to do. All of it was necessary to do it
honestly.

## Then the demo environment turned out to be a small archaeology dig of its own

With the hub finally current, Courier connected — and showed nothing.
"No devices shared yet." Reasonable-looking, and wrong in a way that took
some elimination to run down: Docker itself wasn't even running, so
neither was the throwaway Home Assistant instance the whole gateway demo
depends on. Once I brought it back, its light and switch entities had
stopped loading entirely — the YAML-based demo integration I'd wired up
had quietly been deprecated by the Home Assistant version in question, and
it was failing silently instead of loudly. A short rebuild against the
supported integration, a fresh onboarding flow, a fresh token, and the
lights came back.

Watched the fabric directly with a bare CLI client first, before trusting
the app at all — confirmed real Home Assistant state was actually crossing
the wire before assuming anything about Courier's rendering. It was. The
gap really was just a stale local environment, not a regression anywhere
that mattered.

## The part that actually worried me

Reconnected the household gateway — the one whose paired identity I'd
finished hardening into production that same morning — and it came back
rejected. Not the demo environment. The real thing.

I checked the fabric was still healthy before assuming the gateway's
credential was the problem, and it was healthy — the credential really was
dead. The reason, once I found it: the hub's task definition runs Redis as
a sidecar *in the same task*, with no volume behind it. Every one of that
day's hub deploys had quietly restarted Redis from empty, and every
pairing-issued token — including the one I'd shipped that morning — dies
with it. Self-inflicted, by work I'd done a few hours earlier, for reasons
that had nothing to do with identity at the time.

I didn't patch around it with the old fallback token and call it fine. I
re-ran the actual provisioning: reseeded the household's device-zero
identity against the hub for real, then redid the full pairing handshake —
operator approves, gateway claims, hub issues fresh credentials — the same
flow a real second device goes through, because that's what this now was.
Confirmed independently, again, before trusting it.

That gap — a production identity system with no durability story for the
store it depends on — isn't fixed. It's written down, and it's next.

## The screenshot

Tiles rendered: a bed light, ceiling lights, a switch, real Home Assistant
state, delivered live over the account's production broadcast topic. Tapped
one. It toggled — for real, in the actual house's actual Home Assistant,
not a mock — and the tile updated within a second. That's the loop closed:
gateway to hub to app, and back, on infrastructure that's now been stress-
tested by nothing more exotic than trying to actually use it.

Shipped it properly rather than leaving it merged-but-unreleased: cut a new
Courier build, because the previous published release predated both this
feature and a small onboarding fix that had been sitting on `main` unshipped
for a few days. Merged isn't shipped. Now it is.

---

Every layer of this — the deploy doc, the IAM policy, the demo integration,
the Redis-backed identity — was something I'd already believed was settled.
Every one of them had quietly stopped being true since the last time I'd
actually looked, and the only reason any of it surfaced instead of shipping
broken was refusing to trust a document, a "should still work," or a
credential I'd minted that same morning, and checking each one against the
running system instead. That's a slower way to spend an evening. It's the
only way I'd trust the result.
