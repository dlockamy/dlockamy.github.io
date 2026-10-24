---
layout: post
title: "What a Kit Is"
# Alternate titles (3 to 8 words, no comma, no "and"): "The Kits Are Opening"; "Building One Kit Twice".
date: 2026-10-26
published: false # DRAFT: remove this line when ready to publish
categories: [slashbuilder, ai]
tags: [slashbuilder, kits, beos, architecture, ai-assisted-development, series]
excerpt: "Part 2 of the series on the platform I'm building with AI. What a Kit is: a small building block named for the thing it owns, with a stable interface, a list of things it refuses to do, and a rule that products compose Kits and never fork them. Then one Kit in practice, built twice, and the Kits starting to open."
image: /images/what-a-kit-is.png
author: Douglas Lockamy
ai_assisted: true
---

In [Part 1](/posts/2026/10/19/where-an-os-idea-started/) I said the idea I
never got over from BeOS was the Kit: a system made of parts with clear edges.
This post is about what I mean by that word, because "Kit" is easy to say and
easy to get wrong.

I first drafted this to stay abstract until the Kits could open. They've
started opening, so this version also shows one Kit in practice.

## The rules

**A Kit is named for the thing it owns.** Not the field it lives in. I had a Kit
named after a whole area of technology, and within weeks a request came up to
put something in it that its own rules forbade, only because the name made it
sound like it belonged. A name that describes a field invites
everything in the field. A name that describes an artifact (bytes, messages, a
manifest) tells you what doesn't belong. I renamed it for what it actually owns.

**A Kit says what it will not do.** Every Kit has a short list of things that
are out of scope, written down on purpose. This turns out to matter more than
the list of what it does. Most of the arguments I've had with myself about where
a feature should live were settled by one line saying "not here."

**A Kit has a stable interface.** Other things build on it, so it doesn't get to
change shape casually. When it does need to change, that's a visible, deliberate
act with a version attached, not a side effect.

**Products compose Kits. They never fork them.** If an application needs
something a Kit doesn't do, the gap gets filed against the Kit. The application
doesn't quietly grow its own private copy of the logic. This is the rule that's
hardest to keep when you're in a hurry, and it's the one that makes the whole
approach worth it.

**The more mature Kits have invariants.** A short list of things that must stay
true, each one backed by a test that would fail if it stopped being true.
Not every Kit has reached this yet.

A Kit is never an application. It holds bytes, or carries messages, or knows
who someone is: something every application would otherwise build for itself,
badly, on a deadline.

## One Kit in practice

The Kit I wanted first from BeOS was the Application Kit, the one that made an
app an app: a name, a place to run, a way to quit. The name is provisional,
because it echoes BeOS and I haven't checked it against existing product names.

Every app I built solved the same small problems again: where its files and
settings live, how to run in a test without touching the real ones, who else is
running, how to quit cleanly.

So I wrote the contract first, as a spec, then had it built twice, in Dart and
in Rust, against one set of shared test cases. The Dart version passed straight
away, which told me less than it seemed to, because the same builder wrote the
code and the tests. The Rust version, built from the written contract, passed
the same tests and still disagreed with Dart on about a dozen things the tests
never asked about. The first implementation had decided them silently. Closing
those took twenty more cases, for 61 in all, and both implementations pass every
one. If you're going to write a contract, build it twice.

Six small apps went on top: a calculator, minesweeper, a notepad, a stopwatch,
a queue of pretend jobs, and a launcher that shows what's running. Each app's
whole `main.dart` is now 5 to 11 lines.

I also counted the helper code the apps wrote for themselves because the Kit
lacked it. It went the wrong way before it went the right way: 727 lines across
the six apps, then 330 after moving the obvious pieces into the Kit. Then I
taught three apps to find and talk to other copies of themselves, and it jumped
to 777, because all three had written the same helpers. Moving those into the
Kit brought it to 164. The rule I took from it: build a Kit piece when the
second app copies it, not before.

The bigger lesson was what the Kit should not decide: what coordination means. A
stopwatch sharing a countdown, a notepad syncing notes and a game handed to
another copy want different things. So the Kit finds the other copies and
carries messages without reading them, and each app writes five small methods
that say what to do. That was plenty for the stopwatch and the handoff, and only
just enough for live play. For the notepad it's a thin shell around about 700
lines of the app's own code, which tells me what the Kit should grow next:
acknowledgements, large transfers, and a way for a late arrival to catch up.

A seventh app tests the other half: a Flutter interface over a Rust core, using
the Application Kit's Rust side and the Kit that holds bytes. In a test on
macOS, syncing a one-byte edit of a 10 MiB note to a second copy moved 0.46% of
the note.

Not verified yet: copies on different machines, a real network, a Linux window,
and release builds.

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

## The Kits are opening

What's real today:

- **The Kit Book**, a documentation site in the spirit of the Be Book. It has a
  status card for every Kit in the registry, 19 of them, public or not, saying
  which are real code and which are still design documents, as the registry
  records them. It also has the Application Kit's reference pages (no other Kit
  has any yet), the demo apps, and a Makefile that sets up, tests and builds
  them.
- **The Application Kit's repository**, provisional name, Limits section and all.
- **The Hearth specification**, which was already public.

A few more Kits may follow. I'll name them when they're ready.

<!-- GO-LIVE: before publishing, https://kits.slashbuilder.com must return 200 and serve the Kit Book, and slash-builder/kit-book must be public. If either is not true, delete the "Read the Kit Book" line below AND the Kit Book bullet above (see drafts/part-2-kit-book-notes.md, section C). Delete this comment before publishing. -->

**Read the Kit Book:** [kits.slashbuilder.com](https://kits.slashbuilder.com)

<!-- GO-LIVE: before publishing, https://github.com/slash-builder/application-kit must be public and return 200, its default branch must carry the public release (README titled "Application Kit", with a Limits section), and the repository must still be named application-kit. If not, delete the "Read the Application Kit" line below AND the repository bullet above (see drafts/part-2-kit-book-notes.md, section C). Delete this comment before publishing. -->

**Read the Application Kit:** [github.com/slash-builder/application-kit](https://github.com/slash-builder/application-kit)

The Kits also need a way to talk to each other and to other machines, and that's
the next post: **Hearth**, the protocol, and where the Plan 9 half of the
inspiration comes back in. If you'd like to read ahead:
[github.com/slash-builder/hearth](https://github.com/slash-builder/hearth).
