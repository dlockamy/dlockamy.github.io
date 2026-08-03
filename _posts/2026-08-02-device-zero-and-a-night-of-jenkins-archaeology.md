---
layout: post
title: "Device zero, and a night of Jenkins archaeology"
date: 2026-08-02
categories: [quickring, devops]
tags: [quickring, rust, flutter, jenkins, ci-cd, infrastructure]
excerpt: "Quickring's first-account bootstrap problem finally has real code behind it — a concurrency bug and all. Shipping it to production went cleanly, on purpose. Chasing an unrelated 'the CI build is stuck' report afterward did not go cleanly at all, and turned into four separate Jenkins bugs in one sitting."
author: Douglas Lockamy
ai_assisted: true
---

Quickring's pairing protocol has always had a chicken-and-egg problem at
its center: devices pair into an *existing* account by having an
already-trusted device approve them. That works great for your second
device. It says nothing about your first one — there's no existing
device yet to do the approving.

The design for that (ADR-0004, "device zero": a cloud-held device that
plays the existing-device role for exactly this one bootstrap moment)
has been written for weeks. This weekend it became real code, shipped to
production, and — because that's apparently how every weekend goes lately
— immediately led into an unrelated four-bug Jenkins spelunking session
that started with someone saying "the build seems stuck."

## Device zero, for real

The shape of it: `quickring/hub` grew an admin-only endpoint,
`POST /admin/device0`, that seeds a device's Ed25519 public key and mints
it a bearer token. `quickring/api` — the service that actually handles
account signup — calls that endpoint once per new account, then uses the
exact same `fabric-kit` SDK a real device would use to connect as device
zero, initiate a pairing session, and auto-approve whatever claims it.
Device zero isn't a special code path in the protocol. It's an ordinary
client that happens to be controlled by a server instead of a phone.

That symmetry is the whole point of the design, and it held up. The part
that didn't come for free was provisioning device zero exactly once per
account.

## The bug that only shows up if you actually run the test

Two people signing up for Quickring for the first time, in two browser
tabs, at the same moment, is a completely normal scenario — not an edge
case, not a race someone invented for the sake of a blog post. My first
pass handled it by generating a keypair, registering it with the hub,
*then* writing it to DynamoDB with a conditional check so only one
writer's row survives.

That's wrong, and it's wrong in a way that doesn't announce itself.
Registering a key with the hub is a plain overwrite — whichever of the
two concurrent calls happens to land *last* is the key the hub actually
has on file, completely independent of which DynamoDB write wins the
conditional check. So it's entirely possible for caller A's row to win
in DynamoDB while caller B's key is what's registered with the hub. The
account ends up with a persisted identity that doesn't match what the
hub thinks device zero's public key is. Every future pairing approval
from that point on fails signature verification, silently, for an
account that otherwise looks completely healthy.

I only found this because I wrote an integration test that actually
fires two concurrent provisioning calls at a live hub and asserts they
converge on the same, working credentials — and the first version of the
code failed it. The fix flips the ordering: claim the DynamoDB row
*first*, with a conditional write and no bearer token yet, and only the
caller that wins that claim is allowed to talk to the hub at all. Nobody
else ever registers a key for that account, so there's no ordering left
to race. The losing caller just polls briefly for the winner to finish.

I mention this not because concurrency bugs are novel — they aren't —
but because the whole reason this got caught before shipping is
mechanical: the test ran against a real hub, with real concurrent
requests, not a mock standing in for one. A test that asserted the happy
path alone would have shipped this exact bug.

## Shipping it without breaking what was already live

`quickring/api` was already running in production, serving real
Cognito-authenticated traffic. Today's change added three new required
environment variables — `HUB_ADMIN_URL`, `HUB_ADMIN_TOKEN`,
`HUB_WS_URL` — and the service's own startup code refuses to boot if any
of them is missing, no exceptions. That's the right behavior in general.
It also meant a naive deploy of tonight's code, straight onto the
running task definition, would crash-loop the *entire* service —
not just the new endpoint, everything, on a service people were actively
using.

Catching that before it happened was just a matter of reading the
Terraform and the running task definition side by side before touching
anything. The fix was two separate, deliberate steps: apply the new
Secrets Manager entry and environment variables with the image tag
pinned to whatever was *already* running (a config-only change, verified
healthy before moving on), then — only once that landed clean — deploy
the actual new code. Same discipline for the hub side. Both deploys
finished with zero failed tasks, confirmed by comparing the ECS service's
running task-definition ARN against the one Terraform had just
registered, because `aws ecs wait services-stable` will happily report
success even when the deployment circuit breaker quietly rolled back to
the old version underneath it.

None of this is exotic. It's just the difference between "it built" and
"it's actually running the thing I meant to ship," and that gap is where
most of my worst nights have historically come from.

## Then: "the CI build seems stuck"

Separately — genuinely unrelated to any of the above — Courier's Flutter
CI pipeline had a stage that runs on a dedicated macOS build agent for
the iOS/macOS builds, and that agent was offline. Reasonable ask: make
the Android and Darwin build legs independently toggleable, so a
build can go green on Linux/Android alone while the Mac agent is down.

Should be a small change. It was not a small change, because chasing it
downhill turned up three more bugs that had nothing to do with the
offline agent.

**Bug one, the actual ask.** Declarative Jenkins pipelines let you skip a
stage with a `when` block, but if that stage also declares its own
`agent { label 'darwin' } }`, Jenkins evaluates the agent *before* it
checks whether to skip the stage — meaning the pipeline still blocks
forever waiting for a node that was never coming, even with a
technically-correct skip condition sitting right there. The fix needs an
explicit `beforeAgent: true` on the `when` block. Miss that one flag and
the whole feature silently does nothing.

**Bug two, found trying to prove the fix worked.** With the darwin stage
correctly skipped, the *Linux* stage still failed — Flutter's own base
image (`ghcr.io/cirruslabs/flutter`) could never be pulled. The org
folder's Jenkins configuration sets a default Docker registry for every
build in it, and that registry turned out to be `build.softsurve.com` —
which, checked directly, is just our own Jenkins controller. Not a
registry. A 404, no `WWW-Authenticate` header, nothing that looks like a
Docker API at all.

Fixing the hostname wouldn't have been enough either. The *correct* Nexus
host exists and works fine — except its Docker proxy is bound to exactly
one upstream, Docker Hub, the way every Nexus Docker proxy repository is.
It has no concept of "pull from wherever the image name says" the way a
generic mirror would. `ghcr.io/cirruslabs/flutter` was never going to
resolve through it, correct hostname or not, because it's a different
registry entirely.

The actual fix sidesteps the whole mechanism: instead of Jenkins'
declarative `agent { docker { image ... } }` shorthand (which is
specifically what triggers the org folder's default-registry injection),
a manually scripted `docker.image(...).inside(...)` call never goes
through that code path at all. Confirmed live — a clean, direct
`docker pull ghcr.io/cirruslabs/flutter:3.44.0`, no Nexus involved,
first try.

**Bug three, found poking at why a Jenkins job didn't exist yet.**
Turns out neither `quickring/api` nor `quickring.me` had a Jenkins job at
all, days after their Jenkinsfiles were committed. The org folder scans
for new repos on a four-hour timer, not a webhook, and nothing had
triggered a manual scan since. A one-line API call fixed the immediate
problem; the underlying "new repo, silent for up to four hours" gap is
still there.

**Bug four, found while writing up bug three.** The vault I keep studio
context in had a note claiming the *real*, actively-scanned Jenkins
folder for this org lived at a different path entirely —
`personal-computing/quickring.cd/...`. Checked directly against the
running controller, twice: that folder doesn't exist. It's what a
Terraform-adjacent config template in another repo *would* produce, if
anyone had ever applied it. Nobody had. The note had been written by
reading the template and assuming it described reality, which is exactly
the mistake this entire post is about avoiding, and I'd made it myself
in a document I otherwise trust. Corrected it in place rather than let
two contradictory claims sit next to each other for the next person (or
the next me) to trip over.

By the time all four were sorted, the actual feature request — a working
toggle for an offline build agent — was maybe 10% of the diff.

## The one I'm not calling done

While all this was happening, the build agent also ran out of disk space
mid-build — unrelated to any of the above, just old Docker layers piling
up. That part's an easy, known fix: `docker system prune`, ~30GB back.

What's not easy is what happened immediately after. Three consecutive
builds, right after the cleanup, failed on a *missing Jenkins
credential* — one that had worked fine in every build earlier that same
night. It's not courier-specific; it's the credential nearly every
pipeline in the studio uses for Nexus. I don't know yet whether that's a
coincidence, a flake, or something the cleanup actually broke, and I'd
rather say that plainly than paper over it with a guess. It's first on
the list for next time, and it's written down where I'll actually see it
before assuming anything else is wrong.

---

Two threads, one weekend: a real distributed-systems bug caught by a
test that was actually run against real infrastructure, and a build
pipeline that turned out to be wrong in four independent ways once
someone finally looked closely at it instead of just re-running it. Same
lesson both times, really — the thing that looks like it should obviously
work is worth checking directly, especially when checking it costs you
twenty minutes and being wrong about it costs you a debugging session six
weeks from now.
