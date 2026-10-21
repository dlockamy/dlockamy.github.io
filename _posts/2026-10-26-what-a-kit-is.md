---
layout: post
title: "What a Kit Is"
date: 2026-10-26
published: false # DRAFT: remove this line when ready to publish
categories: [slashbuilder, ai]
tags: [slashbuilder, kits, beos, architecture, ai-assisted-development, series]
excerpt: "Part 2: what I mean by a Kit, the rules every one follows, and why that shape suits building with AI."
image: /images/what-a-kit-is.png
author: Douglas Lockamy
ai_assisted: true
---

In [Part 1](/posts/2026/10/19/where-an-os-idea-started/) I said the idea I
never got over from BeOS was the Kit: a system made of parts with clear edges.
This post is about what I mean by that word, because "Kit" is easy to say and
easy to get wrong.

A note on scope before I start. This is deliberately not a status report. The
set of Kits is still moving, some are real code and some are design documents,
and I would rather show you specifics once they've settled and I'm ready to open
them up than give you a snapshot that's wrong by next month. What I can do now
is explain the rules, because the rules are the part I'm confident about.

## The rules

**A Kit is named for the thing it owns.** Not the field it lives in. I learned
this the hard way. I had a Kit named after a whole area of technology, and within
weeks a request came up to put something in it that its own rules forbade, for
no better reason than that the name made it sound like it belonged. The name
was the problem. A name that describes a field invites everything in the field.
A name that describes an artifact (bytes, messages, a manifest) tells you what
doesn't belong. I renamed it for what it actually owns.

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
Not every Kit has reached this yet, and I won't pretend otherwise.

## What kinds of Kit there are

Without naming any of them, the shapes look like this:

- something that holds bytes and knows how to find them again
- something that carries messages between processes and between machines
- something that knows who someone is, and what they're allowed to do
- something that describes what a device can do
- something that builds an image of the system
- something that gives every application the same look and feel

None of those is an application. Every one is something an application would
otherwise have to build for itself, badly, on a deadline.

## Why Kits and AI suit each other

This is the thesis behind the whole experiment. A Kit is a small, bounded piece
with a clear interface and tests, which is exactly the shape of work an AI can do
well and a reviewer can check.

In practice it has looked like this:

- **Reviewers with different briefs.** I have AI reviewers read the same design,
  one briefed as a data modeler and another as a security engineer. They find
  different problems. Neither replaces the other, and both are cheaper than
  finding the problem after it ships.
- **Testing the tests.** An AI that writes the code also writes the tests, which
  is a conflict of interest. One check I use is mutation testing: deliberately
  breaking the code one line at a time, flipping a comparison or deleting a
  check, and seeing whether the tests notice. A suite that looks thorough and
  misses a mutation is telling you something. It has found real bugs in code I'd
  have called finished.
- **Applications that push back.** When an application is built on a Kit and
  hits a gap, the finding gets written down against the Kit. In one case an
  application found real problems in a Kit on its first day of use, and they
  were fixed the same day.

Here's where it goes wrong, and it's a good example of the caveats I promised in
Part 1: a Kit can be written much faster than its neighbours can be reconciled.
For a while I had documentation that disagreed with itself about how many Kits
there were. Each page was right on the day it was written. That's a real cost of
building quickly with AI, and I'd rather tell you about it than hide it.

## Where this is going

Some Kits are real code with real tests, and some are design documents that
haven't earned code yet. I'm not going to rank them in public until I'm sure I'm
describing what's there and not what I hope is there.

The Kits also need a way to talk to each other and to other machines, and that's
the next post: **Hearth**, the protocol, and where the Plan 9 half of the
inspiration comes back in. The specification is already public if you'd like to read ahead:
[github.com/slash-builder/hearth](https://github.com/slash-builder/hearth).
