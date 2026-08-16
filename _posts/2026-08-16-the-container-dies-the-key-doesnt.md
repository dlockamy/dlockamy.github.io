---
layout: post
title: "The container dies, the key doesn't, and the same flaw one layer up"
date: 2026-08-16
categories: [quickring, security]
tags: [quickring, rust, cryptography, hpke, security, design-review, jenkins, ci-cd]
excerpt: "A throwaway sentence about virtual devices turned into a household security model in one sitting. Then someone who hadn't written it looked at it and found a flaw that would have shipped as a working feature. Then, hours later, the same class of flaw turned up again one layer up — and that second time is the part actually worth writing down."
author: Douglas Lockamy
ai_assisted: true
---

Quickring has a bootstrap problem I've written about before: devices join
an account by having an already-trusted device approve them, which is a
lovely story for your second device and says nothing at all about your
first. The answer I shipped a couple of weeks ago was "device zero" — a
cloud-held device that plays the already-trusted role for exactly that one
moment.

Tonight I said something offhand about it that I did not expect to spend
the rest of the night on:

> Maybe we have two types of virtual device, device-0 and device-1. I think
> root for our definition translates as full access, not a precise user.

That's it. That's the whole prompt. Out of it came a real household
security model, a flaw in that model found before a line of code existed
to implement it, and then — hours later, one layer up — the same kind of
flaw again.

## Root as a capability, not a name

The first half of that sentence is the useful half. If "root" is a
*named user*, then the whole household security model becomes a question
of who that user is, whether they can be impersonated, and what happens
when they leave. If "root" is a *capability* — a thing you hold, where
anyone holding it has full access and nobody has it ambiently — the
question changes into something much easier to reason about and much
harder to get quietly wrong. No ambient authority, in the Fuchsia sense:
you don't get power by being someone, you get it by holding a handle.

The second half gives you the bootstrap. device-0 is a containerized
gateway that starts with no key at all, generates a household authority
root, spawns the household, and is plumbed to accept exactly one user —
the one who called it into existence. That user gets onboarded, gets
root, and device-0 dies. It exists for one purpose and its whole
lifecycle is that purpose.

Written down that way it looks finished. It wasn't.

## The flaw that a working feature would have hidden

I had the design validated rather than built — handed off to be checked,
not implemented, by someone other than the person who wrote it. That
distinction turns out to matter more than which someone.

The problem it found: in the model as I first specified it, device-0
generates the household's permanent signing authority and hands it over
at bootstrap. Same key going in as coming out. The handover is a change
of custody, not a change of key.

Which means the ephemerality I was so pleased with buys nothing. "Dies"
describes the container. It does not describe the key. A signing key
scraped out of container memory during a thirty-second bootstrap window
is exactly as valid three years later, and nothing anywhere in the system
would ever detect that it had been copied — because a valid signature
from the authority root *is* the authorization. There's no second thing
to check it against. One memory read of that container, ever, and the
household is permanently compromised by an attacker who never has to
touch it again.

This is not a hypothetical pattern I talked myself into. It is what the
already-shipped code does today. `quickring/api/src/device0.rs` calls
`DeviceKeypair::generate()` server-side, takes the resulting 32-byte
Ed25519 seed, hex-encodes it, and writes it to DynamoDB as
`device0_seed_hex`, where it stays. The module's own header comment is
honest about it — a persisted seed is a durable, replicated,
subpoena-able asset. I knew that when I wrote it, in a context where
device zero was a convenience and not the root of a household's trust.
Promote the same pattern to "this key is the household's authority
forever" and the same line of code becomes a very different thing.

The fix landed in the same design pass, and it's small: device-0 mints an
authority root, the *real* first device generates its own authority root
locally, device-0 signs a one-time transition attestation binding
old-root to new-root, publishes it, and then dies. The household's actual
authority never existed anywhere device-0 could touch. Anything scraped
out of that container afterwards authorizes exactly nothing, because the
key it would authorize against has already been rotated away by a device
the operator never had.

Ephemerality was never the mitigation. Rotation is. Ephemerality just
made me feel like I'd already done the work.

## Then it happened again, four hours later, one layer up

This is the part I actually want on record.

Later the same night I was writing the full end-to-end encryption design —
the real one, the document that has to be true before anybody says the
words "end-to-end encrypted" out loud. And the same class of gap turned
up in a fix that had *shipped that same night*.

Earlier in the evening I'd added pairing attestations: when a device
approves a new device, the approver signs the new device's identity key.
That gives you something genuinely valuable — a phone can prove
cryptographically that a specific human tapped approve on a specific
device, and the roster stops being "whatever the hub told me" and becomes
a chain of device-signed claims. Good fix. Correct fix. Working, tested,
merged.

It signs the identity key. A device needs a *second* key to receive
encrypted content — a sealing key, the X25519 public key that content
gets wrapped to. The attestation didn't cover it.

So the sealing key would have arrived with no path back to the human
approval step at all. The only thing vouching for it would have been the
server. Which is the exact attack the attestation scheme was built to
prevent — a hub substituting a key of its choosing into the roster — now
reappearing at the one layer where it would actually get someone's
content read. The identity key would have been beautifully attested and
completely beside the point.

Found and fixed before anything shipped with the gap in it. The
attestation material becomes v2, domain-separated, covering both keys,
with the v1 form staying verifiable for devices already attested under
it.

Twice in one sitting. Two flaws, at two different layers, in two things I
had already mentally filed as done. Here's what they had in common, and
it's the whole lesson: **neither one would have failed any test that
checks whether the feature works.** Both features worked. The pairing
attestation attested. The bootstrap bootstrapped. Every one of those
tests passes on the broken version. The flaws were only visible from a
completely different question — not "does this do what it says" but "what
does an attacker walk away with" — and that question is very hard to ask
honestly about a design you just finished being pleased with.

The thing that caught both was having it checked by someone who hadn't
written it. I'd love to claim more insight than that. It's mostly just
that.

## A dependency list built to trip someone up on purpose

Some real code did come out of the night: the device key-generation
primitives in `fabric-kit`. RFC 9180 HPKE via `hpke` 0.12 —
DHKEM(X25519, HKDF-SHA256), HKDF-SHA256, ChaCha20-Poly1305 — plus
`ed25519-dalek` 2 and `chacha20poly1305` 0.10.

The more interesting part is what's *not* in that dependency list, and
why. `hkdf`, `sha2`, and `x25519-dalek` are all deliberately absent, and
the Cargo.toml says so in a comment. The design says there is no key
derivation anywhere in this layer — a household root that derives every
device key means anyone holding the root derives every device key, which
is precisely the failure mode of the first flaw wearing a different hat.
So the crate is built to not have the tools to do it. If a future pull
request adds `hkdf` to `fabric-kit`, that's not a normal dependency
bump; it's a signal to go re-read that section of the design before
approving.

`x25519-dalek` is out for a plainer reason: the sealing keypair gets
minted and serialized through `hpke`'s own KEM API and nowhere else. Two
paths to the same key is two chances to disagree about what that key is.

None of that enforces anything. It just makes a specific mistake visible
in a diff, to a reviewer who may well be me, six months from now, having
completely forgotten I did this.

## Three unrelated things that were also true

Not everything tonight was crypto.

A CI pipeline for one service had been silently failing **every single
pull request**, for reasons that had nothing whatsoever to do with the
code under test: a Jenkins stage was trying to start a container from an
image that a previous, skipped stage had never built. Every PR looked
broken. Not one of them was. One line to fix, once somebody finally
looked at the failure instead of assuming they knew what it meant. I
don't know how long it had been like that and I'm not sure I want to.

A "flaky test" turned out not to be flaky. The test constructor said, in
its own comments, that it was safe for parallel runs — written in good
faith, genuinely believed, and wrong: it shared a single real file on
disk across every test that used it. It never failed locally. Not once in
51 verification runs. It needed a specific flavor of bad timing that my
machine simply doesn't produce and real CI does. Root-caused rather than
retried-until-green, which is the only version of that investigation
worth doing.

And a near-miss I'd rather write down than not: two separate lines of
work ended up editing the same shared checkout at the same time, and one
kept quietly reverting the other's changes to the same file. It surfaced
only because I noticed a file I had just edited had changed underneath
me, and stopped to check instead of shrugging it off as a tool glitch.
Nothing was lost. It was close, and the thing that saved it was a
suspicion, not a safeguard, which is not a control I can rely on twice.

## What is still not true

The content encryption this whole night was in service of **is not
live**. The design is finished, the threat model is written, real
primitives exist and compile. None of it is wired into anything a user
can touch. There is no shipping build of Quickring that encrypts your
content end-to-end.

So the download page came down. Not softened, not caveated — pulled,
rather than leave a claim standing in front of a product that doesn't do
the thing yet. The design document is equally blunt about a claim I will
*never* get to make under this architecture: "it is cryptographically
impossible for us to read your data" would require hardware attestation
or a bootstrap that doesn't run on my infrastructure, and neither of
those exists here. Better to know which sentences are permanently off the
table before writing marketing copy than after.

---

The pattern I keep landing on: the failures that matter least are the
ones where something is broken, because broken announces itself. The ones
that matter are where something works exactly as designed and the design
gives away more than intended. Both of tonight's would have shipped as
features. Both would have passed review by the person who wrote them,
because they *did* — twice, by me, hours apart.

What's next is smaller and duller than the design work: wire the
primitives into an actual device flow, get the v2 attestation covering
both keys in real code, and put the download page back up when the thing
behind it does what the page says. Merged isn't shipped, and designed
isn't merged.
