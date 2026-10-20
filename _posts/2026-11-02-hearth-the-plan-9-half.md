---
layout: post
title: "Hearth: The Plan 9 Half"
date: 2026-11-02
published: false # DRAFT: remove this line when ready to publish
categories: [slashbuilder, ai]
tags: [slashbuilder, hearth, plan9, 9p, protocol, ai-assisted-development, series]
excerpt: "Part 3 of the series on the platform I'm building with AI. Part 1 was the BeOS half of the inspiration. This is the Plan 9 half: Hearth, a small open protocol that borrows 9P's discipline and applies it to a household instead of a data center."
image: /images/hearth-the-plan-9-half.png
author: Douglas Lockamy
ai_assisted: true
---

In [Part 1](/posts/2026/10/19/where-an-os-idea-started/) I said the idea came
from two places. BeOS gave me the Kit: a system made of parts with clear edges,
which [Part 2](/posts/2026/10/26/what-a-kit-is/) was about. This post is the
other half. Plan 9 gave me a way to think about machines talking to each other,
and the thing I built from it is called **Hearth**.

Unlike most of what I've written about this project so far, Hearth is
specific, because the specification is already public. You can read it, and
you can check what I say here against it:
[github.com/slash-builder/hearth](https://github.com/slash-builder/hearth).

## What it is

Hearth is an open protocol for distributed personal resources. The short
version in its own README is "9P-inspired: Plan 9's addressing model, reapplied
to a household instead of a data center. Capability grants instead of accounts;
a thin wire contract instead of a platform."

It sells nothing. It's stewarded by SlashBuilder, the open-source side of the
studio, and a consumer product called Quickring is built on top of it. That
separation is deliberate: the protocol is meant to be implementable by someone
who has never heard of me.

## What I took from 9P

I did not copy 9P's encoding. Hearth uses protobuf, not 9P's hand-rolled binary
format. What I took is the discipline, and the spec says so in as many words:

- **A small, fixed set of message types.** In version 1 there are 24 envelope
  variants: nine request/response pairs, one error, and five server pushes. The
  goal is to stay under 30 for the life of the protocol. The number matters less
  than the habit: every new message type has to earn its place, and the usual
  answer is that it should have been a new *step* of an existing interaction
  instead.
- **Every request gets exactly one answer.** Requests carry a tag; the response
  carries the same tag. Anything the server pushes on its own is a visibly
  separate category with no tag at all. There is no fourth kind of message.
- **Errors are first-class.** Any request can be answered with an error carrying
  its tag.
- **Multi-step conversations use a handle the server hands out**, rather than
  inventing a new message type per step. That's the move 9P's `walk` makes, and
  it's the one I find myself reaching for most.
- **It's versioned from message one.** Version negotiation happens before any
  other traffic.

If you've read the 9P papers, none of this will surprise you. That's the point.
I'm not claiming a new idea; I'm claiming the old one still works.

## The two layers

The standard has two layers, and both are defined in the same document so a
reader never has to chase a second spec. The **base layer** is the envelope, tag
correlation, the request/response/push grammar, errors and addressing. The
**fabric layer** is everything that's only true because the message crossed a
network: sessions, publish and subscribe, device pairing, presence, catching up
after being offline, and end-to-end encryption.

The reason for the split is a property I care about: a message should be the
same message whether it's going to another process on the same machine or to a
device across the country. Crossing the boundary changes the transport and
nothing else. What gets sent is never translated on the way.

## How it travels

The network leg is a WebSocket carrying one protobuf envelope per binary frame,
with a 1 MiB cap per message. Anything bigger, like a file, deliberately never
goes through the hub. The spec points to peer-to-peer transfer or to references
into content-addressed storage instead. A hub that only relays small messages has much less to carry, and much less to
lose.

## What I'd rather you knew

I promised in Part 1 to tell you where this goes wrong, so here are the real
ones, taken from the repository's own notes.

- **It still carries the old name.** The spec is titled "Quickring Wire
  Protocol," the schema package is `quickring.v1`, and the WebSocket subprotocol
  string says the same. A coordinated rename is tracked, and it's a breaking
  change, so it hasn't happened yet.
- **The documents lag the code in places.** The encryption design document was
  written before any of it was implemented and kept saying so for weeks after it
  shipped. It has since been corrected where I checked it against running code,
  and the repository says plainly that other sections have not been re-audited.
  I'd rather a spec admit that than look finished.
- **Some of it is still a design.** The spec lists what's deliberately not in
  version 1, including file transfer, federation between hubs and team topics.
  Those are decisions to wait, not gaps I forgot.

## Why it belongs in this series

The Kits are the parts, and Hearth is how the parts, and the machines they run
on, find and talk to each other without anyone having to trust a platform. A Kit
that carries messages between processes and a protocol that carries them between
machines are meant to be the same shape on purpose.

Next I want to go back to the AI side of the experiment and look at what building
this way has actually cost and bought.
