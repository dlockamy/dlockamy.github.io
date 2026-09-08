---
layout: post
title: "The near-empty repo that wasn't: verifying a refactor before you plan it"
date: 2026-09-07
categories: [devops, architecture]
tags: [rust, protobuf, sha256, jenkins, ci-cd, git, monorepo, kits, refactoring]
excerpt: "I scoped a two-week refactor last week — pulling shared logic out into standalone Kits — and the most useful thing I did all week was not write any of it. Three verification passes, run before the plan was allowed to harden, each turned up the codebase quietly contradicting an assumption the plan was about to rest on. A repo that looked near-empty was twelve commits behind. A doc that said a feature didn't exist was two PRs out of date. And a Kit meant to replace 'legacy' code turned out to be the stub, while the legacy code was the thing that actually worked."
author: Douglas Lockamy
ai_assisted: true
---

The work I set out to plan last week is boring in the good way: take
logic that several products share, extract it into standalone versioned
libraries — I call them Kits — and have the products depend on the
published Kit instead of carrying their own copy. The rule the whole
thing exists to enforce is simple to state and hard to keep: *products
compose Kits; Kit logic never forks back into a product.* The refactor
is about making that true in code, not just true on a slide.

That's a two-week shape. The temptation with a two-week shape is to
spend an afternoon reading, form a mental model, and start scoping the
slices. I did the first part. Then, before letting the plan harden, I
ran three separate verification passes against the parts of the model I
was least sure about. All three came back wrong, and each one was wrong
in a way that would have quietly poisoned the plan built on top of it.

This is a post about those three passes, because the plan itself is the
easy part. The credibility of a plan is entirely downstream of whether
the facts under it are real, and the git history was telling me at least
three things that weren't.

## Pass one: the repo that looked near-empty

The first Kit I went to scope was `message-kit` — the messaging
substrate a couple of products lean on. I opened my local clone, read
through it, and came away thinking it was close to greenfield: a
skeleton, some type stubs, not much wired together. Fine, I thought;
that makes the extraction easy, there's barely anything there to move.

That was completely wrong, and the reason is embarrassing in the way
that the useful lessons usually are. My local clone was twelve commits
behind `origin/main`. On the remote, `message-kit` already carried a
fully-built router, messenger, and handler implementation — roughly
eleven hundred lines of it. The "near-empty skeleton" I'd been reading
was a real, working thing frozen at an old point in its own history,
and my editor had shown me the past with total confidence.

If I'd scoped the extraction against that read, the plan would have
budgeted days to *write* code that already existed, and — worse — it
would have proposed a shape that ignored the shape the code had already
grown into. You cannot plan an extraction around a snapshot. The single
cheapest habit I took away from the week: `git fetch` and diff against
`origin/main` *before* you form an opinion about what a repo contains,
not after the opinion has already set.

## Pass two: the doc that was two PRs out of date

The second pass was against a piece of provisioning functionality I
believed was unbuilt. I believed it because a doc in the repo said so,
in plain language, in a section that read like current state.

The doc was stale. The feature had shipped — across two separate PRs
that had merged and moved on — and the doc had simply never been
updated to notice. Prose does not have a test suite. A comment or a
design note that was true when it was written will keep asserting its
truth long after the code underneath it has changed, and nothing in the
repo will flag the drift. Code at least fails a build when it lies;
documentation just keeps saying the old thing in a confident voice.

The lesson here is narrower than pass one but sharper: when a doc claims
something *isn't* built, that's a claim to verify against the code and
the merge history, not a fact to plan around. "Not built yet" is
exactly the kind of assumption a two-week plan loves to inherit,
because it justifies scope. It's also exactly the kind of assumption
that's cheap to check and expensive to be wrong about.

## Pass three: the stub that was supposed to be the replacement

The third one is my favorite, because it inverts the intuition you'd
bring to the whole exercise. I went to look at `substrate-kit`, a Kit
whose job is to replace an older runtime implementation — the kind of
thing you'd assume, from the naming and the framing, is the modern
version superseding the legacy one.

It was the other way around. `substrate-kit` was largely a stub —
`principal.rs` plus scaffolding — while the "legacy" code it was
notionally replacing, an 846-line `docker_runtime.rs`, was the piece
that actually ran. The new thing had the aspirational name and the
clean charter; the old thing had the working behavior. If the plan had
treated the Kit as "the real implementation, just needs extracting" and
the runtime as "the thing we're deleting," it would have scheduled the
deletion of the only code in that pair that worked.

Naming encodes intent, and intent is not status. The thing labeled
new/canonical/next is a statement about where you *want* to go. Whether
it's arrived is a separate question that only the code can answer, and
the code answered no.

## The precondition that actually let it proceed: sha256, not vibes

Here's the part that turns this from a horror story into a plan. The
one assumption the extraction genuinely could not survive being wrong
about was the wire schema. Both `message-kit` and the fabric layer
carried their own vendored copy of the protobuf schema, and the entire
premise of extracting a shared messaging Kit is that everyone is
speaking the same wire format. If those two copies had drifted — even
by a field number, even by an enum value — then "consume the shared
Kit" would silently change bytes on the wire, and prost stores enums as
`i32`, so the failure would be quiet and downstream and awful to trace.

I did not want to eyeball that. I `sha256`'d both vendored copies and
confirmed they were byte-identical. That single hash comparison is the
load-bearing precondition of the whole refactor: it's the one thing
that made it safe to proceed *despite* the stale-clone scare in pass
one. The schema was provably the same on both sides, so consolidating
onto one owned copy is a mechanical move, not a semantic one. A
diff-by-hash is worth more than any amount of "they look the same to
me," and it's the difference between a plan that rests on a fact and a
plan that rests on a hope.

## The CI regression I found by trying to land something

While all this was going on, a related but separate push tripped over
something worth naming on its own, because it's the exact failure mode
this whole post is about — a green signal that isn't measuring what you
think it's measuring.

Trying to land a fabric-layer version bump (PR #65), the merge gate went
red for no reason the code could explain. The code was fine; the real
test job passed when I queried Jenkins directly. What had happened is
that the `pr-merge` GitHub status context for the repo had been silently
repointed — sometime after an earlier merge — away from the real test
job and onto a release/packaging pipeline that never runs tests at all.
So the status that was supposed to mean "the tests passed" now meant
"the packaging step ran," which is a completely different and much
weaker claim wearing the same badge.

This is pass-one-through-three in miniature: a signal everyone trusts,
quietly detached from the thing it's supposed to represent, still
reporting with full confidence. It's a live CI-gating regression that
affects every future PR on that repo, not a one-off. The fix rebased
the bump onto a corrected gate and re-verified against the real job —
not the badge — before merging.

## Why I pulled the calendar gate off this work

There was an open question of whether this refactor should wait behind a
scheduled milestone or run in parallel with it. I decided to run it in
parallel, and the reasoning is worth quoting straight from my own notes
rather than paraphrasing into something tidier:

> "fixing it saves work later and breaking up into kits gives us smaller
> build/test cycles... each kit can have its own test suite."

That's the real argument for the Kit model, stripped of ceremony.
Smaller units have smaller, faster, more honest test cycles. A Kit with
its own suite tells you something specific when it goes red; a product
that carries a fork of that Kit's logic tells you nothing until it's
too late and gives you a merge conflict for your trouble. The calendar
gate was protecting a sequencing that the architecture didn't actually
need.

## The plan, and what it's allowed to assume

With the three passes done and the schema hash confirmed, the scoped
shape came out as three slices:

- **CLUS-44** — merge the outstanding `message-kit` work (PR #6) and
  freeze the v0.1 public surface, so downstream consumers have a stable
  thing to depend on.
- **QR-213** — a golden-vector wire-compatibility suite: pinned,
  known-good encoded messages that fail the build the instant the wire
  format shifts, so the byte-identical guarantee from the sha256 check
  becomes a permanent gate instead of a one-time observation.
- **QR-214** — move the fabric layer onto the *published* `message-kit`
  and delete its vendored schema copy, which is the whole point: one
  owner of the wire format, everyone else a consumer.

Each of those rests on a fact I verified rather than an impression I
formed. That's the only thing that makes the plan worth the paper.

## What's actually landed since I scoped this

I'm writing this a little over a week after the scoping, and in the
spirit of not pretending a plan is a shipment: some of it has since
gone in, and it's more honest to say exactly what than to leave the
impression that any of this is finished.

The `message-kit` work merged — PR #6 landed on the 28th, and the v0.1
surface freeze plus the golden-vector wire-compat gate merged the next
day; the pinned vectors and the frozen public re-exports are in the
tree now. The fabric layer has since been rebased onto the published
`message-kit` envelope with its vendored schema deleted, which is the
consolidation those three passes existed to make safe. And the CI-gate
regression got fixed, which unblocked the version bump (PR #65) that
first surfaced it. Beyond that the wave is still in motion — several
pieces are gated on a Linux runner (the runtime bus needs `AF_UNIX
SOCK_SEQPACKET`, which macOS doesn't have) and on a couple of
decisions that aren't mine alone to make. I'm not going to inventory a
Kit roster here, because that count is genuinely in flux this week and
any number I wrote down would be stale by the time you read it — which
is, if you've read this far, exactly the mistake this whole post is
about.

---

The honest shape of the week: the most valuable work was the work that
produced no code. Three verification passes, an afternoon of `git
fetch` and `sha256sum` and reading merge history instead of reading
snapshots, and the plan came out resting on things that are true. The
alternative — the version of me that scoped confidently off a
twelve-commit-stale clone, a stale doc, and a misleading name — would
have produced a beautiful two-week plan built on three facts the
codebase was quietly contradicting, and I'd have found out which ones
somewhere around day eight.

A stale clone is worse than an empty one, because an empty repo tells
you the truth. The clone told me a story with total confidence, and the
only reason the plan survived is that I checked the story against the
remote, the merge log, and a hash before I let myself believe it.

If you're about to scope something multi-week off a repo you "know,"
fetch it first. The thing you're sure is empty might be eleven hundred
lines you're about to rewrite.
