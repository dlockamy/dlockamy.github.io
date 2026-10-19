---
layout: post
title: "Where an OS Idea Started"
date: 2026-10-19
categories: [slashbuilder, ai]
tags: [slashbuilder, kits, hearth, benixos, beos, plan9, ai-assisted-development, series]
excerpt: "For years I've had a large OS platform project in mind. A couple of months ago I bet that AI could finally get it off the back burner. It's making progress, so this is the start of a series about the SlashBuilder Kits: what they are and what they're for. Part 1 is where the idea came from: BeOS and Plan 9."
image: /images/where-an-os-idea-started.png
syndicate: true
author: Douglas Lockamy
ai_assisted: true
---

For years I've had a large OS platform project in mind. Between the day job
and general life, it always got pushed off.

A couple of months ago I decided to roll the dice on AI as a way to finally
take it off the back burner and test some ideas. Guess what: it's making
progress. In fact, I think there's enough progress to talk about it.

This is the start of a series covering the work. The project makes heavy use of
AI, so if you're not a fan of AI-powered development, this probably isn't the
series for you. If you are curious, I'll try to be specific about what the AI
did, what I did, and what broke.

The series is about the **SlashBuilder Kits**: the reusable building blocks the
whole platform is meant to be assembled from. Three parts to start:

1. **Start of an idea** (this post): where the thinking came from.
2. **Kits**: what a Kit is, and why I chose that shape.
3. **Hearth**: the protocol that ties the Kits together.

---

## Two footnotes that shaped a career

So much of the inspiration for my tech career comes down to two things: BeOS and
Plan 9.

Neither is much more than a footnote in the larger tech story today. But at the
tail end of the '90s they each carried a pile of novel ideas, and they showed how
much potential there is in trying something new, even if it doesn't work out in
the long run.

### BeOS

My first real encounter with BeOS was on the first PC I ever bought for myself:
a Gateway 2000 P2 with a 10GB hard drive that I was sure I would never fill up.

What amazed me was that you couldn't crash it by simply using it. You could push
RAM and CPU to 100% and everything just kept working. There was no lag in the UI
at all. If things got heavy, you started closing stuff and the load came back
down, like turning down a dial.

This was right around the first trailer for Star Wars Episode I, and the party
trick of the moment was opening dozens of copies of the trailer at once to see
where your machine gave up. BeOS kept playing them. On the same hardware,
Windows struggled to play a single video, and it certainly couldn't run two,
much less a dozen or more.

BeOS was a desktop operating system built from scratch for the media-heavy
machines of its day, rather than as a descendant of an older design. The
things people still talk about:

- It was **pervasively multithreaded** and responsive under load, at a time when
  that was not the norm on a desktop.
- Its filesystem kept **queryable attributes** on files, so "find" worked more
  like a database than a directory walk.
- It was organized as a set of **Kits**: coherent, documented API groups (the
  Application Kit, Interface Kit, Media Kit, Storage Kit, and so on) that an
  application composed rather than reimplemented.

That last one is the idea I never got over. A system whose parts have clear
edges, stable interfaces, and names that say what they're for is a system a
small team (or one person) can actually hold in their head.

### Plan 9

I came to Plan 9 through reading: a lot of research, and a lot of the papers on
both Plan 9 and Inferno. Inferno was the first spark. Here was an operating
system that could be entirely self-contained and still use 9P to mount resources
over the network.

What took it from interesting to amazing was the demo for the
[Octopus project](https://lsub.org/octopus/), the ultimate extension of the
Plan 9 and 9P ideas that I had seen. As the project describes it, the idea is to
distribute a system by centralizing all of it on a personal computer and
connecting the devices around you to that one machine.

In the demo, an ad hoc group of devices really did act as one machine. The video
that did it for me is
[Using upperware in Octopus](https://web.archive.org/web/20110902230213/http://lsub.org/ls/export/demos/upperware1-mid.mp4),
a walk through a series of demonstrations: using one computer to send text to
speech out of another machine, or telling one machine to have another machine's
webcam take a picture, and then watching that picture appear as the front window
on a third. (The project's own site no longer hosts it, so that link is to the Internet
Archive's copy, which downloads as an MP4.)

The pieces of Plan 9 that stuck with me:

- **Everything is a file**, and this time they meant it. Network connections,
  windows, and processes all show up as files you can read and write.
- **Per-process namespaces.** Each process can assemble its own view of the
  system, which makes "bring the remote thing here and treat it like it's local"
  a normal operation instead of a special case.
- **One small protocol, 9P**, to speak to all of it, local or remote.

Both systems had the same instinct underneath: pick a small number of strong
ideas, apply them everywhere, and let the system get simpler as it grows rather
than more tangled.

## Why now, and why AI

We started using AI more at work, and I have a habit with every tool we use
there: I feel the need to deep dive on it at home and push it to its limits.
Then I bought into the $100 tier of Claude, and it felt like if I was going to
spend that, I had better go all in and make something happen with it.

The obvious candidate was the project that had been on the back burner for
years. An OS platform isn't one project. It's dozens of projects that have to
agree with each other, which is exactly the part that never fit into evenings
and weekends.

What I wanted to find out was narrow: could AI be the thing that makes a
Kit-shaped system tractable for one person with a day job? Not "can it write an
OS." Could it help me build many small, well-bounded pieces, each with a clear
interface, and keep them consistent with one another?

The answer so far is "more than I expected, with caveats," and the caveats are
most of what this series is about.

## Where this is going

I'm not going to claim it's finished, because it isn't. Some of the Kits are
real code with real tests, some are still design documents, and the set is still
moving. Part 2 is about what a Kit is and why I chose that shape. I'll go into
specifics on individual Kits later, once they've settled and I'm ready to open
them up.

Part 3 is about **Hearth**, the protocol, which is where the Plan 9 side of the
inspiration comes back in.
