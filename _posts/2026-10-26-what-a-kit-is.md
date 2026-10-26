---
layout: post
title: "What a Kit Is"
# Alternate titles (3 to 8 words, no comma, no "and"): "The Kits Are Opening"; "Parts With Clear Edges"; "Building One Kit Twice".
date: 2026-10-26
published: false # DRAFT: remove this line when ready to publish
categories: [slashbuilder, ai]
tags: [slashbuilder, kits, beos, plan9, architecture, ai-assisted-development, series]
excerpt: "Part 2: what I mean by a Kit, where the idea comes from, the rules every Kit follows, and an honest look at where the Kits stand today. The first ones are opening up."
image: /images/what-a-kit-is.png
author: Douglas Lockamy
ai_assisted: true
---

Last week I started a series about a project I've carried around for years: a
large, modern operating system platform, assembled from reusable parts I call
Kits. Between the day job and general life it always got pushed aside. A few
months ago I decided to bet that AI could help one person finally get it moving,
and it has. This series is the record of that: what the AI did, what I did, and
what broke.

If you missed [Part 1](/posts/2026/10/19/where-an-os-idea-started/), here's the
short version. Two old operating systems shaped how I think about building
software. BeOS stayed fast and responsive under load, and it was organized as a
set of Kits. Plan 9 treated everything as a file and tied machines together with
one small protocol. Neither won, and both had ideas I never got over. The Kit is
the one this post is about.

"Kit" is easy to say and easy to get wrong, so here's the plan. First, what I
mean by a Kit and the rules every one follows. Then one Kit up close, so it
isn't all abstract. Then an honest look at where the Kits stand today, and what
you can actually go and read.

## Where the idea comes from

BeOS was organized as a set of Kits: the Application Kit, the Interface Kit,
the Media Kit, the Storage Kit. Each was a coherent, documented group of
interfaces that an application composed instead of rebuilding, and the Be Book
documented them well enough that the whole system felt small enough to hold in
your head.

Plan 9 contributes the other half. It picked a few strong ideas, per-process
namespaces and one small protocol for talking to everything, and applied them
everywhere, so the system got simpler as it grew instead of more tangled.
That half shows up in Part 3.

What I took from both is a way of building: pick the pieces carefully, give each
one a clear edge, and let everything else compose them. A Kit is my version of
that piece.

## The rules

**A Kit is named for the thing it owns.** Not the field it lives in. I had a Kit
named after a whole area of technology, and within weeks a request came up to
put something in it that its own rules forbade, only because the name made it
sound like it belonged. A name that describes a field invites everything in the
field. A name that describes an artifact (bytes, messages, a manifest) tells you
what doesn't belong. I renamed it for what it actually owns.

**A Kit says what it will not do.** Every Kit has a short list of things that
are out of scope, written down on purpose. This matters more than the list of
what it does. Most of the arguments I've had with myself about where a feature
should live were settled by one line saying "not here."

**A Kit has a stable interface.** Other things build on it, so it doesn't get to
change shape casually. When it does change, that's a visible, deliberate act
with a version attached, not a side effect.

**Products compose Kits. They never fork them.** If an application needs
something a Kit doesn't do, the gap gets filed against the Kit. The application
doesn't quietly grow its own private copy of the logic. This is the rule that's
hardest to keep when you're in a hurry, and it's the one that makes the whole
approach worth it.

**The more mature Kits have invariants.** A short list of things that must stay
true, each backed by a test that would fail if it stopped being true. Not every
Kit has reached this yet.

A Kit is never an application. It holds bytes, or carries messages, or knows who
someone is: something every application would otherwise build for itself,
badly, on a deadline.

## One Kit, up close

The Kit I wanted first from BeOS was the Application Kit, the one that made an
app an app: a name, a place to run, a way to quit. Mine is called App Context
Kit. It borrows its idea from the BeOS Application Kit; it is not a
reimplementation of it and is not affiliated with Haiku.

Every app I built solved the same small problems again: where its files and
settings live, how to run in a test without touching the real ones, who else is
running, how to quit cleanly. The Kit solves them once. Three things from
building it are worth passing on.

**Build it twice.** I wrote the contract first, as a spec, and had it built in
Dart and in Rust against one set of shared test cases. The Dart version passed
straight away, which told me less than it seemed to, because the same builder
wrote the code and the tests. The Rust version, built from the written contract,
passed the same tests and still disagreed with Dart on about a dozen things the
tests never asked about. Closing those took twenty more cases, and both
implementations now pass all 61.

**Build a piece when the second app copies it.** I put the Kit under seven small
apps (a calculator, minesweeper, a notepad and so on) and counted the helper code
each one wrote because the Kit lacked it. The count went up before it came down,
because three apps had each written the same helpers. Moving those into the Kit
brought it back down. The rule I took from it is to wait for the second copy.

**Don't decide what the app means.** A stopwatch sharing a countdown and a
notepad syncing notes want different things from "coordination." So the Kit
finds the other copies of an app and carries messages without reading them, and
the app supplies a few small methods that say what to do. That was plenty for
some apps and only just enough for others, which tells me what the Kit should
grow next.

The details are in the Kit Book, not here.

## Why Kits and AI suit each other

A Kit is a small, bounded piece with a clear interface and tests, which is
exactly the shape of work an AI can do well and a reviewer can check. Building
it twice is one check. Two others:

- **Reviewers with different briefs.** AI reviewers read the same design, one
  briefed as a data modeler and another as a security engineer. They find
  different problems.
- **Testing the tests.** An AI that writes the code and the tests has a conflict
  of interest. Mutation testing breaks the code one line at a time and checks
  whether the tests notice. It has found real bugs in code I'd have called
  finished.

Here's where it goes wrong: a Kit can be written much faster than its neighbours
can be reconciled. When I generated a status card for every Kit from the
registry, several entries disagreed with their own repositories. One claimed a
language its repository doesn't contain. Others were still marked as design
documents after quietly growing skeleton code with tests. The cards are
generated, so fixing the registry fixes them.

## Where the Kits stand

I'd rather be plain about this than impressive. The registry lists 19 Kits:

- **2 are pre-release.** Used by other parts of the platform, with an API that
  is settling but not frozen.
- **11 are alpha.** Real code and tests exist, but expect the API to change.
- **4 are still design documents.** There's no code to speak of yet.
- **1 is banked and 1 is legacy.** Kept in the catalog for the record.

(The App Context Kit is new and isn't in that count yet.) Almost all of them are
still private: until now only one Kit's repository was public, along with the
Hearth specification. This post is the start of opening more.

What I'm opening first:

- **The Kit Book**, a documentation site in the spirit of the Be Book. It has a
  status card for every Kit, public or not, saying plainly which are real code
  and which are still design documents. It also has the App Context Kit's
  reference pages, the demo apps, and a Makefile that sets up, tests and builds
  them.
- **The App Context Kit's repository**, with its tests running on GitHub Actions
  (Linux, macOS and Windows) and a Limits section that says what isn't verified.
  Copies of an app on different machines over a real network, a real Linux
  desktop, and signed release builds are all still unverified. The Rust crate
  isn't on crates.io yet.
- **The Hearth specification**, which was already public.

I'll open more Kits when each one is ready, and I'll say so here when I do. The
set is still moving. I'm not going to pretend it's stable.

<!-- GO-LIVE: before publishing, https://kits.slashbuilder.com must return 200 and serve the Kit Book, and slash-builder/kit-book must be public. If either is not true, delete the "Read the Kit Book" line below AND the Kit Book bullet above (see drafts/part-2-kit-book-notes.md, section C). Delete this comment before publishing. -->

**Start with the Kit Book:** [kits.slashbuilder.com](https://kits.slashbuilder.com).
The [Kit catalog](https://kits.slashbuilder.com/30-kits/) has every card, and
[Start here](https://kits.slashbuilder.com/10-start-here.html) takes you from an
empty folder to a running demo app.

<!-- GO-LIVE: before publishing, https://github.com/slash-builder/app-context-kit must be public and return 200, its default branch must carry the public release (README titled "App Context Kit", with a Limits section and the BeOS lineage sentence), and the repository must be named app-context-kit, and its latest CI run on main must be green on Linux, macOS and Windows (the bullet above says so). If not, delete the "Read the App Context Kit" line below AND the repository bullet above (see drafts/part-2-kit-book-notes.md, section C). Delete this comment before publishing. -->

**Read the App Context Kit:** [github.com/slash-builder/app-context-kit](https://github.com/slash-builder/app-context-kit)

If something in the book is confusing, wrong, or oversold, that's useful to
know. Open an issue on the repository.

The Kits also need a way to talk to each other and to other machines, and that's
the next post: **Hearth**, the protocol, and where the Plan 9 half of the
inspiration comes back in. If you'd like to read ahead:
[github.com/slash-builder/hearth](https://github.com/slash-builder/hearth).
